"""Tarkash Video Studio. Local API separated from UI for future site integration."""
import copy
import functools
import hashlib
import io
import json
import math
import os
import re
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from brand_palette import extract_palette

from renderer import ROOT, FFMPEG, SlideBrowser, render_batch, sections_for, local_asset, utf16_length
from speech import voices, voice_catalog, voice_engine, require_voice, synthesize, PREVIEW_TEXT
import natural_speech

for folder in ['data','assets/uploads','outputs','previews','web']:
    (ROOT/folder).mkdir(parents=True,exist_ok=True)
app=FastAPI(title='Tarkash Video Studio',docs_url='/api/docs')
PROJECT=ROOT/'data'/'project.json'
DEFAULT=ROOT/'data'/'default-project.json'
PREVIEW_REVISION=hashlib.sha256(b''.join((ROOT / name).read_bytes() for name in ('renderer.py', 'intro_cover.py', 'video_screens.py', 'video_design.css', 'content_design.css'))).hexdigest()
jobs={}
jobs_lock=threading.Lock()
project_lock=threading.Lock()
preview_lock=threading.Lock()
executor=ThreadPoolExecutor(max_workers=1)

@app.middleware('http')
async def local_only(request:Request, call_next):
    host=request.headers.get('host','').split(':')[0]
    if host not in ('127.0.0.1','localhost','testserver'):
        return JSONResponse({'detail':'This studio only accepts local connections.'},status_code=403)
    origin=request.headers.get('origin')
    if request.method not in ('GET','HEAD','OPTIONS') and origin and origin not in ('http://127.0.0.1:8765','http://localhost:8765'):
        return JSONResponse({'detail':'Cross-origin writes are blocked.'},status_code=403)
    length=int(request.headers.get('content-length','0') or 0)
    if length>30*1024*1024:
        return JSONResponse({'detail':'Upload limit is 30 MB.'},status_code=413)
    return await call_next(request)

def atomic_json(path,obj):
    temporary=path.with_suffix('.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)

def validate(project):
    if not isinstance(project,dict): raise HTTPException(422,'Project must be an object.')
    project=copy.deepcopy(project)
    if not isinstance(project.get('version',1),int) or project.get('version',1) not in (1,2): raise HTTPException(422,'Unsupported project version.')
    for key,default in [('title','MORNING ACTION'),('intro','')]:
        project.setdefault(key,default)
        if not isinstance(project[key],str) or len(project[key])>3000: raise HTTPException(422,f'{key} must be text, up to 3,000 characters.')
    if not isinstance(project.get('settings',{}),dict): raise HTTPException(422,'Settings must be an object.')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(project.get('date',''))): raise HTTPException(422,'Choose a valid YYYY-MM-DD date.')
    try: datetime.strptime(project['date'],'%Y-%m-%d')
    except ValueError: raise HTTPException(422,'Choose a valid date.')
    if not isinstance(project.get('sections'),list) or not 1<=len(project['sections'])<=30: raise HTTPException(422,'Project needs 1 to 30 shared sections.')
    if not isinstance(project.get('brands'),list) or not 1<=len(project['brands'])<=40: raise HTTPException(422,'Project needs 1 to 40 brands.')
    for group in [project['brands'],project['sections'],project.get('insightsSections',[])]:
        if not isinstance(group,list) or len(group)>40: raise HTTPException(422,'Invalid section collection.')
        ids=[]
        for item in group:
            if not isinstance(item,dict) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,70}',str(item.get('id',''))): raise HTTPException(422,'Each brand and section needs a safe, unique id.')
            ids.append(item['id'])
        if len(ids)!=len(set(ids)): raise HTTPException(422,'Duplicate brand or section ids are not allowed.')
    for s in project['sections']+project.get('insightsSections',[]):
        if s['id'] in ('intro','ending'): raise HTTPException(422,'intro and ending are reserved section ids.')
        for key in ('title','body','narration'):
            s.setdefault(key,'')
            if not isinstance(s[key],str): raise HTTPException(422,f'Section {key} must be text.')
        if not isinstance(s.get('enabled',True),bool): raise HTTPException(422,'Slide inclusion must be true or false.')
        if len(str(s.get('body','')))>18000 or len(str(s.get('narration','')))>18000: raise HTTPException(422,'Section text is too long.')
        line_styles=s.get('lineStyles',[])
        if not isinstance(line_styles,list) or len(line_styles)>len(s['body'].split('\n')) or any(style not in ('auto','normal','heading1','heading2') for style in line_styles):
            raise HTTPException(422,'Paragraph styles must match the lines in the slide content.')
        inline_formats=s.get('inlineFormats',[])
        if not isinstance(inline_formats,list) or len(inline_formats)>400:
            raise HTTPException(422,'Too many selected-text styles.')
        for mark in inline_formats:
            if not isinstance(mark,dict) or type(mark.get('start')) is not int or type(mark.get('end')) is not int or not 0<=mark['start']<mark['end']<=utf16_length(s['body']):
                raise HTTPException(422,'Selected-text styles must refer to valid content text.')
            kind=mark.get('kind')
            if kind in ('bold','italic','underline','strike','highlight'):
                valid=set(mark)=={'start','end','kind'}
            elif kind=='size':
                valid=set(mark)=={'start','end','kind','value'} and type(mark.get('value')) is int and 20<=mark['value']<=60
            elif kind=='color':
                valid=set(mark)=={'start','end','kind','value'} and isinstance(mark.get('value'),str) and bool(re.fullmatch(r'#[a-fA-F0-9]{6}',mark['value']))
            else:
                valid=False
            if not valid:raise HTTPException(422,'Choose a valid selected-text style.')
        try: duration=float(s.get('duration',5))
        except (ValueError,TypeError): raise HTTPException(422,'Section duration must be a number.')
        if not math.isfinite(duration) or not 2<=duration<=900: raise HTTPException(422,'Section duration must be 2–900 seconds.')
        if not isinstance(s.get('rows',[]),list) or len(s.get('rows',[]))>40 or any(not isinstance(r,dict) for r in s.get('rows',[])): raise HTTPException(422,'Invalid table rows.')
        for row in s.get('rows',[]):
            if any(not isinstance(row.get(k,''),str) or len(row.get(k,''))>500 for k in ['metric','nifty','sensex','bankNifty']): raise HTTPException(422,'Table values must be text of 500 characters or fewer.')
    for b in project['brands']:
        # Older projects saved company-specific voices. A batch now uses only
        # the narrator selected in project settings for every company.
        b.pop('voice',None)
        if not isinstance(b.get('name'),str) or not b['name'].strip(): raise HTTPException(422,'Every brand needs a name.')
        for key in ('logo','website','phone','email','address','disclaimer','socialText','instagram','facebook','twitter','ending_text','footer_note','introTitle'):
            if key in b and (not isinstance(b[key],str) or len(b[key])>18000): raise HTTPException(422,f'Brand {key} must be text, up to 18,000 characters.')
        if 'art' in b and (not isinstance(b['art'],dict) or any(not isinstance(x,str) for x in b['art'].values())): raise HTTPException(422,'Artwork must map section names to image paths.')
        try: ending_duration=float(b.get('endingDuration',10))
        except (ValueError,TypeError): raise HTTPException(422,'Closing duration must be a number.')
        if not math.isfinite(ending_duration) or not 2<=ending_duration<=900: raise HTTPException(422,'Closing duration must be 2–900 seconds.')
        for key in ('primary','accent'):
            if not re.fullmatch(r'#[a-fA-F0-9]{6}',str(b.get(key,''))): raise HTTPException(422,'Brand colours must be six-digit hex colours.')
        if b.get('endingStyle') not in ('contact','disclaimer','combined','follow'): raise HTTPException(422,'Choose a supported closing style.')
    settings=project.setdefault('settings',{})
    if not isinstance(settings.get('voice',''),str): raise HTTPException(422,'Choose a voice from the voice list.')
    if settings.get('voice','').startswith('kokoro:') and settings['voice'].removeprefix('kokoro:') not in natural_speech.VOICE_NAMES:
        raise HTTPException(422,'Choose one of the listed AI voices.')
    for key in ('narration','readDisclaimer'):
        if key in settings and not isinstance(settings[key],bool): raise HTTPException(422,'Narration options must be true or false.')
    for key,default,low,high in [('speechRate',0,-5,5),('musicVolume',.12,0,.5)]:
        try: value=float(settings.get(key,default))
        except (ValueError,TypeError): raise HTTPException(422,f'{key} must be a number.')
        if not math.isfinite(value) or not low<=value<=high: raise HTTPException(422,f'{key} must be between {low} and {high}.')
    if not isinstance(settings.get('music',''),str): raise HTTPException(422,'Background music must be an uploaded audio path.')
    if settings.get('quality') not in ('720p','1080p'): raise HTTPException(422,'Quality must be 720p or 1080p.')
    if settings.get('voiceEngine','windows') not in ('windows','kokoro'): raise HTTPException(422,'Choose a supported voice option.')
    settings['voiceEngine']=voice_engine(settings.get('voice',''))
    if len(json.dumps(project))>1_500_000: raise HTTPException(422,'Project exceeds size limit.')
    return copy.deepcopy(project)

def get_project():
    project=json.loads((PROJECT if PROJECT.exists() else DEFAULT).read_text(encoding='utf-8'))
    # v1 always rendered the comic closing for Insights; preserve that appearance
    # now that users can explicitly choose a different closing layout in v2.
    if project.get('version',1)<2:
        for brand in project.get('brands',[]):
            if brand.get('layout')=='insights' and brand.get('endingStyle')=='combined':
                brand['endingStyle']='follow'
        project['version']=2
    return project

@app.get('/api/health')
def health(): return {'app':'tarkash-video-studio','version':'1.0.0'}

@app.get('/api/project')
def project_get(): return get_project()

@app.put('/api/project')
@app.post('/api/project/import')
def project_put(project:dict):
    project=validate(project)
    with project_lock: atomic_json(PROJECT,project)
    return project

@app.get('/api/project/export')
def project_export():
    return JSONResponse(get_project(),headers={'Content-Disposition':'attachment; filename="tarkash-project.json"'})

@functools.lru_cache(maxsize=1)
def system_voices(): return voices()

@app.get('/api/status')
def status():
    project=get_project()
    folder=ROOT/'videoes'
    excluded=[str(p.relative_to(folder)) for p in folder.rglob('*.mp4') if p.parent!=folder] if folder.exists() else project.get('excluded',[])
    browser=any((ROOT/'.runtime/browsers').glob('chromium*/chrome-win*/chrome.exe')) or any(p.exists() for p in [Path(os.environ.get('LOCALAPPDATA',''))/'Google/Chrome/Application/chrome.exe',Path('C:/Program Files/Google/Chrome/Application/chrome.exe')])
    return {'ffmpeg':Path(FFMPEG).is_file(),'browser':browser,'voices':voice_catalog(system_voices()),'naturalVoices':natural_speech.status(),'excluded':excluded,'sourceCount':len(project['brands']),'platform':'Windows','voiceEngine':'local'}


@app.post('/api/voice-preview')
def voice_preview(payload:dict):
    voice=payload.get('voice','')
    rate=payload.get('speechRate',0)
    if not isinstance(voice,str) or len(voice)>200: raise HTTPException(422,'Choose a listed voice.')
    try: rate=float(rate)
    except (ValueError,TypeError): raise HTTPException(422,'Choose a speaking pace between -5 and 5.')
    if not math.isfinite(rate) or not -5<=rate<=5: raise HTTPException(422,'Choose a speaking pace between -5 and 5.')
    try:
        require_voice(voice,system_voices())
        path,duration=synthesize(PREVIEW_TEXT,{'voice':voice,'speechRate':rate},ROOT/'previews'/'voices')
    except Exception as error:
        raise HTTPException(422,str(error)) from error
    name=next((item['name'] for item in voice_catalog(system_voices()) if item['id']==voice),'Default Windows voice')
    return {'url':'/previews/voices/'+path.name,'duration':round(duration,2),'voice':voice,'name':name,'text':PREVIEW_TEXT}

@app.post('/api/upload')
async def upload(file:UploadFile=File(...)):
    raw=await file.read(30*1024*1024+1)
    if len(raw)>30*1024*1024: raise HTTPException(413,'Maximum file size is 30 MB.')
    extension=Path(file.filename or '').suffix.lower()
    palette=None
    if extension in ('.png','.jpg','.jpeg','.webp'):
        try:
            im=Image.open(io.BytesIO(raw));im.load()
            if im.width*im.height>40_000_000: raise ValueError('Image exceeds 40 megapixels.')
            palette=extract_palette(im)
            destination=ROOT/'assets/uploads'/(uuid.uuid4().hex+'.png')
            im.thumbnail((4096,4096));im.convert('RGBA' if 'A' in im.getbands() else 'RGB').save(destination)
        except (UnidentifiedImageError,ValueError,OSError,Image.DecompressionBombError) as error: raise HTTPException(422,'Please upload a valid PNG, JPEG or WebP image.') from error
    elif extension in ('.mp3','.wav','.m4a'):
        destination=ROOT/'assets/uploads'/(uuid.uuid4().hex+extension)
        destination.write_bytes(raw)
    else: raise HTTPException(422,'Upload PNG, JPEG, WebP, MP3, M4A or WAV.')
    return {'url':'/assets/uploads/'+destination.name,'palette':palette}


@app.post('/api/logo-palette')
def logo_palette(payload:dict):
    path=local_asset(payload.get('url'))
    if not path: raise HTTPException(404,'Choose an uploaded logo first.')
    try:
        with Image.open(path) as image:
            palette=extract_palette(image)
    except (UnidentifiedImageError,ValueError,OSError,Image.DecompressionBombError) as error:
        raise HTTPException(422,'Please choose a valid logo image.') from error
    return {'palette':palette}

def find_brand(project,brand_id):
    brand=next((b for b in project['brands'] if b['id']==brand_id),None)
    if not brand: raise HTTPException(404,'Brand not found.')
    return brand

@app.post('/api/preview')
def preview(payload:dict):
    project=validate(payload.get('project',get_project()))
    brand=find_brand(project,payload.get('brandId'))
    section_id=payload.get('sectionId','intro')
    section=next((s for s in sections_for(project,brand) if s['id']==section_id or s.get('sourceId')==section_id),None)
    if section is None:
        section=next((s for s in project['sections']+project.get('insightsSections',[]) if s['id']==section_id),None)
    if section is None: raise HTTPException(404,'Section not found.')
    key=hashlib.sha256(json.dumps([PREVIEW_REVISION,project,brand,section],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:32]
    path=ROOT/'previews'/(key+'.png')
    if not path.exists():
        try:
            with preview_lock:
                if not path.exists():
                    with SlideBrowser() as browser: browser.capture(project,brand,section,path)
        except Exception as e: raise HTTPException(422,str(e))
    return {'url':'/previews/'+path.name}

def public_job(job): return {k:v for k,v in job.items() if not k.startswith('_') and k!='cancel'}

def worker(project,selected,job):
    try:
        job['status']='running'
        render_batch(project,selected,job)
        job['status']='completed';job['message']='All selected videos are ready.'
    except InterruptedError:
        job['status']='cancelled';job['message']='Export cancelled. Completed videos remain available.'
    except Exception as error:
        job['status']='failed';job['error']=str(error);job['message']='Export stopped. Review the error and retry.'
    finally:
        try:
            atomic_json(Path(job['_work'])/'job.json',public_job(job))
        finally:
            with jobs_lock:
                job['_finished']=True

@app.post('/api/jobs')
def create_job(payload:dict):
    project=validate(payload.get('project',get_project()))
    ids=payload.get('brandIds',[])
    if not isinstance(ids,list) or not ids or len(ids)>40 or any(not isinstance(i,str) for i in ids): raise HTTPException(422,'Select one or more valid brands (up to 40).')
    selected=[find_brand(project,i) for i in dict.fromkeys(ids)]
    if project['settings'].get('narration',True):
        try:
            require_voice(project['settings'].get('voice',''),system_voices())
        except ValueError as error: raise HTTPException(422,str(error)) from error
    with jobs_lock:
        if any(j['status'] in ('queued','running') for j in jobs.values()): raise HTTPException(409,'An export is already running. Wait for it or cancel it.')
        job_id=datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
        work=ROOT/'outputs'/job_id;work.mkdir()
        atomic_json(work/'project.json',project)
        job={'id':job_id,'status':'queued','progress':0,'message':'Preparing export…','outputs':[],'error':None,'_work':str(work),'cancel':False,'_finished':False}
        atomic_json(work/'job.json',public_job(job))
        jobs[job_id]=job
        executor.submit(worker,project,selected,job)
    return {'id':job_id}

@app.get('/api/jobs')
def list_jobs():
    with jobs_lock:
        result={p.parent.name:json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'outputs').glob('*/job.json')}
        for key,job in result.items():
            if key not in jobs and job['status'] in ('queued','running'):
                job.update(status='failed',message='Export interrupted by a studio restart.',error='Start the export again to finish all selected brands.')
        result.update({key:public_job(job) for key,job in jobs.items()})
    return sorted(result.values(),key=lambda j:j['id'],reverse=True)

@app.get('/api/jobs/{job_id}')
def job_get(job_id:str):
    if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[a-f0-9]{6}',job_id): raise HTTPException(404,'Export not found.')
    with jobs_lock:
        if job_id in jobs: return public_job(jobs[job_id])
        path=ROOT/'outputs'/job_id/'job.json'
        if path.exists():
            result=json.loads(path.read_text(encoding='utf-8'))
            if result['status'] in ('queued','running'):
                result.update(status='failed',message='Export interrupted by a studio restart.',error='Start the export again to finish all selected brands.')
            return result
    raise HTTPException(404,'Export not found.')

@app.post('/api/jobs/{job_id}/cancel')
def cancel_job(job_id:str):
    with jobs_lock:
        if job_id not in jobs or jobs[job_id].get('_finished',False): raise HTTPException(404,'Active export not found.')
        jobs[job_id]['cancel']=True
    return {'ok':True}


@app.delete('/api/jobs/{job_id}')
def delete_job(job_id:str):
    if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[a-f0-9]{6}',job_id):
        raise HTTPException(404,'Export not found.')
    output_root=(ROOT/'outputs').resolve()
    path=output_root/job_id
    with jobs_lock:
        job=jobs.get(job_id)
        if job and not job.get('_finished',False):
            raise HTTPException(409,'This export is still running. Wait for it to finish before deleting it.')
        if path.is_symlink() or not path.is_dir() or path.resolve().parent!=output_root or not (path/'job.json').is_file():
            raise HTTPException(404,'Export not found.')
        try:
            shutil.rmtree(path)
        except OSError as error:
            raise HTTPException(500,f'Could not delete this batch: {error.strerror or error}') from error
        jobs.pop(job_id,None)
    return {'ok':True,'id':job_id}

for folder in ['assets','previews','outputs']:
    app.mount('/'+folder,StaticFiles(directory=ROOT/folder),name=folder)
app.mount('/',StaticFiles(directory=ROOT/'web',html=True),name='ui')
