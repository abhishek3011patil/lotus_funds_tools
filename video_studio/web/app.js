/* Tarkash Video Studio — local, dependency-free editing interface. */
'use strict';

const state = {
  project: null, status: {}, tab: 'content', contentKey: 'sections', sectionId: null, brandId: null,
  previewSection: null, previewUrl: '', previewError: '', previewBusy: false,
  error: '', saveLabel: 'Saved locally', selected: new Set(), jobs: [], historyLimit: 8,
  emojiField: null, saveTimer: null, previewTimer: null, pollTimer: null,
  saveVersion: 0, previewVersion: 0, exporting: false, saving: null, introOpen: false, textStyleOpen: false,
  voicePreview: null, voicePreviewError: '', voicePreviewBusy: false,
  voicePreviewVersion: 0, voicePreviewController: null,
};
const icons = {
  edit: '<path d="m16 3 5 5-12 12-6 1 1-6L16 3Z"/><path d="m14 5 5 5"/>',
  palette: '<path d="M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 1-3.7 1.8 1.8 0 0 1 1-3.3h2a4 4 0 0 0 4-4c0-4-4-7-9-7Z"/><path d="M7 10h.01M10 6.5h.01M15 7h.01M6.5 14h.01" stroke-width="3"/>',
  export: '<path d="M12 3v12m-4-4 4 4 4-4M5 14v6h14v-6"/>',
  upload: '<path d="M12 15V3m-4 4 4-4 4 4M5 14v6h14v-6"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  chevronDown: '<path d="m6 9 6 6 6-6"/>',
  layers: '<path d="m12 3 10 5-10 5L2 8l10-5Zm-10 9 10 5 10-5M2 17l10 5 10-5"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 6-6 4 4 3-3 5 5"/>',
  mic: '<rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8"/>',
  play: '<path d="m9 5 11 7-11 7V5Z"/>',
  film: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18M17 3v18M3 8h4m-4 8h4M17 8h4m-4 8h4"/>',
  smile: '<circle cx="12" cy="12" r="9"/><path d="M8 14c1 4 7 4 8 0M8 8h.01M16 8h.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  plus: '<path d="M12 4v16M4 12h16"/>',
  trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
  folder: '<path d="M3 6a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6Z"/>',
  refresh: '<path d="M20 8a8 8 0 0 0-14-3L3 8m0-5v5h5m-4 8a8 8 0 0 0 14 3l3-3m0 5v-5h-5"/>',
  shield: '<path d="m12 2 9 4v6c0 6-9 10-9 10S3 18 3 12V6l9-4Z"/><path d="m8 12 3 3 5-6"/>',
  globe: '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.info}</svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
const safeUrl = value => /^(\/(?!\/)|https?:\/\/|data:image\/(?:png|jpeg|webp|gif);base64,)/i.test(String(value || '')) ? esc(value) : '';
const currentBrand = () => state.project.brands.find(brand => brand.id === state.brandId) || state.project.brands[0];
const currentSections = () => state.project[state.contentKey] || state.project.sections;
const currentSection = () => currentSections().find(section => section.id === state.sectionId) || currentSections()[0];
const brandSections = brand => brand && brand.useSharedContent === false && Array.isArray(state.project.insightsSections) ? state.project.insightsSections : state.project.sections;
const activeSections = () => state.project.sections.filter(section => section.enabled !== false);
const brandInitials = brand => (brand.name || 'Brand').split(/\s+/).slice(0, 2).map(word => word[0]).join('').toUpperCase();
const prettyDate = value => { try { return new Intl.DateTimeFormat('en-IN', {day:'numeric',month:'short',year:'numeric'}).format(new Date(`${value}T12:00:00`)); } catch { return value || ''; } };
const runtimeReady = value => value === true || (value && typeof value === 'object' && value.available !== false) || (typeof value === 'string' && value.length > 0);
const engineForVoice = voice => String(voice || '').startsWith('kokoro:') ? 'kokoro' : 'windows';

async function api(path, options = {}) {
  const headers = {...(options.body instanceof FormData ? {} : {'Content-Type':'application/json'}), ...(options.headers || {})};
  const response = await fetch(path, {...options, headers});
  const text = await response.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = {error: text || response.statusText}; }
  if (!response.ok) {
    const message = data.error || data.detail || data.message || `Request failed (${response.status}).`;
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  return data;
}

function normalizeProject(project) {
  if (!project || !Array.isArray(project.sections) || !Array.isArray(project.brands)) throw new Error('This file is not a Tarkash project. It needs content sections and a brand library.');
  project.settings ||= {};
  project.intro ??= 'Early Morning Insightful Analysis';
  project.settings.voiceEngine = engineForVoice(project.settings.voice);
  project.sections.forEach(section => { section.body ??= ''; section.narration ??= ''; section.enabled ??= true; section.duration ??= 8; });
  (project.insightsSections || []).forEach(section => { section.body ??= ''; section.narration ??= ''; section.enabled ??= true; section.duration ??= 8; });
  project.brands.forEach(brand => { brand.enabled ??= true; brand.endingStyle ||= 'combined'; delete brand.voice; });
  return project;
}

async function init() {
  try {
    const results = await Promise.allSettled([api('/api/project'), api('/api/status'), api('/api/jobs')]);
    if (results[0].status !== 'fulfilled') throw results[0].reason;
    state.project = normalizeProject(results[0].value);
    state.status = results[1].status === 'fulfilled' ? results[1].value : {};
    const jobs = results[2].status === 'fulfilled' ? results[2].value : [];
    state.jobs = Array.isArray(jobs) ? jobs : jobs.jobs || [];
    state.brandId = state.project.brands[0]?.id;
    state.sectionId = state.project.sections[0]?.id;
    state.previewSection = state.sectionId || 'intro';
    state.selected = new Set(state.project.brands.filter(brand => brand.enabled !== false).map(brand => brand.id));
    render();
    queuePreview(100);
    pollJobs();
  } catch (error) {
    document.querySelector('#app').innerHTML = `<div class="boot"><div class="brand-symbol">T</div><h1>The studio could not open</h1><p>${esc(error.message)}</p><button class="btn btn-primary" data-action="reload">Try again</button></div>`;
  }
}

function render() {
  if (!state.project) return;
  const oldIntro=document.querySelector('.intro-editor');
  if(oldIntro)state.introOpen=oldIntro.open;
  const oldTextStyle=document.querySelector('.text-style-editor');
  if(oldTextStyle)state.textStyleOpen=oldTextStyle.open;
  const titles = {content:['Your daily edition','Write it once. Make it yours, across every brand.'], brands:['A familiar brand. Every frame.','Your logos, your colors, your closing message.'], export:['Ready for the opening bell.','Turn one edition into a complete set of branded videos.']};
  const [title, description] = titles[state.tab];
  document.querySelector('#app').innerHTML = `
    <div class="app-shell">
      <aside class="sidebar" aria-label="Studio navigation">
        <div class="wordmark"><div class="brand-symbol">T</div><div><strong>tarkash<span style="color:#dc8564">.</span></strong><small>VIDEO STUDIO</small></div></div>
        <div class="sidebar-label">Your workspace</div>
        <nav>
          ${navButton('content','edit','Daily content','01')}
          ${navButton('brands','palette','Brands & endings','02')}
          ${navButton('export','export','Export studio','03')}
        </nav>
        <div class="local-box"><span class="status-dot"></span><div><strong>Your local workspace</strong><p>Projects and exports stay on this computer.</p></div></div>
        <div class="sidebar-bottom"><span>Built for your daily rhythm</span><span>v1.0</span></div>
      </aside>
      <main class="main">
        <header class="topbar"><div class="breadcrumb"><span>Workspace</span><span>/</span><strong>${state.tab === 'content' ? 'Daily content' : state.tab === 'brands' ? 'Brands & endings' : 'Export studio'}</strong></div><div class="topbar-right"><span id="save-state" class="save-state">${icon('check')}${esc(state.saveLabel)}</span><span class="avatar" title="Local studio">TS</span></div></header>
        <div class="workspace">
          <div class="page-heading"><div><div class="eyebrow">The morning market, made yours</div><h1>${title}</h1><p>${description}</p></div><div class="heading-actions"><button class="btn btn-secondary" data-action="backup" title="Download project backup">${icon('export')}<span>Save backup</span></button><button class="btn btn-primary" data-action="${state.tab === 'export' ? 'export' : 'go-export'}" ${state.exporting ? 'disabled' : ''}>${icon(state.tab === 'export' ? 'film' : 'arrow')}<span>${state.tab === 'export' ? 'Generate videos' : 'Export videos'}</span></button></div></div>
          ${state.error ? `<div class="notice error" role="alert">${esc(state.error)}<button data-action="dismiss-error" aria-label="Dismiss error">×</button></div>` : ''}
          <div class="workspace-grid"><div class="editor-column">${state.tab === 'content' ? contentEditor() : state.tab === 'brands' ? brandEditor() : exportEditor()}</div>${previewPanel()}</div>
          ${previewNotes()}
        </div>
      </main>
    </div>`;
  updatePreviewDOM();
}

function navButton(tab, image, label, number) {
  return `<button class="nav-btn ${state.tab === tab ? 'active' : ''}" data-tab="${tab}" title="${label}" ${state.tab === tab ? 'aria-current="page"' : ''}>${icon(image)}<span>${label}</span><span class="nav-number">${number}</span></button>`;
}

function toggle(path, checked, label, options = '') {
  return `<label class="toggle-label"><input type="checkbox" data-path="${path}" ${checked ? 'checked' : ''} ${options}><span class="toggle-track"></span><span>${label}</span></label>`;
}

function field(label, path, value, options = {}) {
  const id = `field-${path.replaceAll('.','-')}`;
  const attributes = `id="${id}" data-path="${path}" ${options.number ? 'data-number="true"' : ''} ${options.optionalNumber ? 'data-optional-number="true"' : ''} ${options.rebuild ? 'data-rebuild="true"' : ''}`;
  let control;
  if (options.select) control = `<select ${attributes}>${options.select.map(item => `<option value="${esc(item.value)}" ${String(value) === String(item.value) ? 'selected' : ''}>${esc(item.label)}</option>`).join('')}</select>`;
  else if (options.textarea) control = `<textarea ${attributes} rows="${options.rows || 4}" placeholder="${esc(options.placeholder || '')}">${esc(value)}</textarea>${options.emoji ? `<div class="text-tools"><button class="emoji-trigger" data-action="emoji" data-field="${id}">${icon('smile')} Add emoji</button><span class="char-count" data-count-for="${id}">${String(value || '').length} characters</span></div>${state.emojiField === id ? emojiPicker(id) : ''}` : ''}`;
  else control = `<input ${attributes} type="${options.type || 'text'}" value="${esc(value)}" ${options.min !== undefined ? `min="${options.min}"` : ''} ${options.max !== undefined ? `max="${options.max}"` : ''} ${options.step ? `step="${options.step}"` : ''} placeholder="${esc(options.placeholder || '')}">`;
  return `<div class="field"><label for="${id}">${label}${options.optional ? '<span class="optional">Optional</span>' : ''}</label>${control}${options.hint ? `<small>${options.hint}</small>` : ''}</div>`;
}

function contentEditor() {
  const project = state.project, sections = currentSections(), section = currentSection(), index = sections.indexOf(section), contentKey = state.contentKey;
  const sourceDate = project.sourceDate || project.sampleDate || '';
  if (!section) return `<div class="panel"><div class="empty-state">No content sections are available in this project.</div></div>`;
  const shortTitle = (s, i) => state.contentKey==='insightsSections' ? (s.title.length>26?s.title.slice(0,23)+'…':s.title) : /news/i.test(s.title) ? `News ${sections.slice(0,i + 1).filter(item => /news/i.test(item.title)).length}` : /trend/i.test(s.title) ? 'Market trends' : /nifty|table/i.test(s.title) ? 'Market table' : 'Morning insight';
  return `
    <div class="session-strip">${icon('layers')}<span>${contentKey==='insightsSections'?'<strong>Lotus Insights has its own source script.</strong> Edit its original content here, or switch it to shared content in Brands & endings.':`<strong>One edition. Multiple brand variations.</strong> Your content flows into brands using the shared script.`}</span><span class="badge">${contentKey==='insightsSections'?'INSIGHTS':'EDIT ONCE'}</span></div>
    <section class="panel">
      <div class="panel-header"><div><h2>Daily content</h2><p class="subtitle">The story behind today’s markets</p></div><span class="badge orange">${sections.filter(item=>item.enabled!==false).length} CONTENT SLIDES</span></div>
      <div class="content-overview">${field('Edition name','title',project.title)}${field('Publishing date','date',project.date,{type:'date'})}</div>
      ${Array.isArray(project.insightsSections) && project.insightsSections.length ? `<div class="script-selector"><label for="script-select">Content script</label><select id="script-select" class="control"><option value="sections" ${contentKey==='sections'?'selected':''}>Shared Morning Action</option><option value="insightsSections" ${contentKey==='insightsSections'?'selected':''}>Lotus Insights · original script</option></select></div>`:''}
      <details class="intro-editor" ${state.introOpen?'open':''}><summary>Opening introduction</summary><div>${field('Opening text','intro',project.intro,{textarea:true,rows:2,emoji:true})}<button class="btn btn-ghost btn-small" data-action="preview-intro">${icon('image')}Preview opening</button></div></details>
      <div class="scene-tabs" role="tablist" aria-label="Content sections">${sections.map((item,i) => `<button role="tab" aria-selected="${item.id === section.id}" class="scene-tab ${item.id === section.id ? 'active' : ''} ${item.enabled === false ? 'disabled-scene' : ''}" data-section="${esc(item.id)}"><span class="scene-index">${String(i+1).padStart(2,'0')}</span>${esc(shortTitle(item,i))}</button>`).join('')}</div>
      <div class="panel-body">
        <div class="scene-heading"><div><h3>${esc(section.title)}</h3><p>Slide ${index+1} of ${sections.length} · ${contentKey==='insightsSections'?'Lotus Insights original':'shared content'}</p></div>${toggle(`${contentKey}.${index}.enabled`,section.enabled !== false,'Include slide','data-rebuild="true"')}</div>
        ${section.enabled === false ? '<div class="section-disabled-note">This slide is hidden from exported videos. You can still edit it here.</div>' : ''}
        ${field('Slide headline',`${contentKey}.${index}.title`,section.title)}
        ${field(Array.isArray(section.rows) ? 'Market summary' : 'Slide content',`${contentKey}.${index}.body`,section.body,{textarea:true,rows:Array.isArray(section.rows)?3:6,emoji:true,placeholder:'Add your market update. Line breaks and emojis are welcome.'})}
        ${textStyleEditor(section,`${contentKey}.${index}`)}
        ${Array.isArray(section.rows) ? tableEditor(section,index) : ''}
        <div class="divider"></div>
        <div class="voice-header">${icon('mic')}<strong>Narration</strong><span class="badge green">FOLLOWS YOUR CONTENT</span></div>
        ${field('Voice script',`${contentKey}.${index}.narration`,section.narration,{textarea:true,rows:2,optional:true,placeholder:'Leave blank to read the headline, content and market table.',hint:'When the content changes, the voice changes with it. Leave blank for automatic sentence breaks. For a custom script, use full stops for clear pauses; line breaks alone may run together. Long scripts stay on their slide; shorten content if the preview reports it does not fit.'})}
        <div class="voice-settings"><div class="field"><label for="daily-voice">Voice for all companies</label><select id="daily-voice" data-path="settings.voice">${voiceOptionsHTML()}</select></div>${field('Minimum duration',`${contentKey}.${index}.duration`,section.duration,{type:'number',number:true,min:3,max:180,step:1,hint:'Seconds · extends to fit voice'})}</div>
        <div data-voice-preview>${voicePreviewHTML()}</div>
      </div>
      <div class="panel-footer"><p>${icon('check')}Changes save automatically on this computer.</p><button class="btn btn-secondary btn-small" data-action="next-section">${index === sections.length-1 ? 'Customize brands' : 'Next slide'}${icon('arrow')}</button></div>
    </section>
    <div class="source-note"><strong>Sample content:</strong> The supplied videos contain dated market commentary${sourceDate?` (${esc(sourceDate)})`:''}. Review all text, prices and the publishing date before generating today’s edition.</div>`;
}

function textStyleEditor(section, path) {
  const fonts=[{value:'auto',label:'Design default'},{value:'arial',label:'Arial'},{value:'georgia',label:'Georgia'},{value:'trebuchet',label:'Trebuchet'},{value:'verdana',label:'Verdana'},{value:'tahoma',label:'Tahoma'}];
  const weights=[{value:'auto',label:'Design default'},{value:'normal',label:'Regular'},{value:'semibold',label:'Semi bold'},{value:'bold',label:'Bold'},{value:'heavy',label:'Extra bold'}];
  const aligns=[{value:'auto',label:'Design default'},{value:'left',label:'Left'},{value:'center',label:'Center'},{value:'right',label:'Right'}];
  const group=(name,label,range)=>{
    const style=section.textStyle?.[name]||{},base=`${path}.textStyle.${name}`;
    const fallback=name==='heading'?(currentBrand()?.layout==='insights'?'#ffffff':currentBrand()?.primary||'#1456a0'):(currentBrand()?.layout==='insights'?'#ffffff':'#1c2a38');
    const custom=/^#[0-9a-f]{6}$/i.test(style.color||'');
    return `<div class="text-style-group"><h4>${label}</h4><div class="text-style-grid">
      ${field('Font',`${base}.font`,style.font||'auto',{select:fonts})}
      ${field('Size in pixels',`${base}.size`,style.size??'',{type:'number',number:true,optionalNumber:true,min:range[0],max:range[1],step:1,placeholder:'Auto'})}
      ${field('Weight',`${base}.weight`,style.weight||'auto',{select:weights})}
      ${field('Alignment',`${base}.align`,style.align||'auto',{select:aligns})}
    </div><div class="style-color-row"><label for="style-color-${name}">Text color</label><input id="style-color-${name}" type="color" data-path="${base}.color" value="${esc(custom?style.color:fallback)}" aria-label="${label} color"><span class="style-color-status">${custom?esc(style.color):'Design color'}</span><button class="btn btn-ghost btn-small" data-style-color-reset="${base}.color" ${custom?'':'disabled'}>Use design color</button></div></div>`;
  };
  return `<details class="text-style-editor" ${state.textStyleOpen?'open':''}><summary>Text appearance <span>Fonts, size, bold, color & alignment</span></summary><div class="text-style-inner">${group('heading','Slide heading',[28,90])}${group('body','Slide paragraphs',[20,60])}<p>Styles apply to this content slide across every selected brand. Design colors follow each company automatically. Large text may need shorter copy to fit.</p></div></details>`;
}

function tableEditor(section,index) {
  const columns = [['metric','Metric'],['nifty','Nifty'],['sensex','Sensex'],['bankNifty','Bank Nifty']];
  return `<div class="field"><label>Market levels</label><div class="table-wrap"><table class="market-table"><thead><tr>${columns.map(([,label])=>`<th scope="col">${label}</th>`).join('')}<th scope="col"><span class="hidden">Actions</span></th></tr></thead><tbody>${section.rows.map((row,rowIndex)=>`<tr>${columns.map(([key,label])=>`<td><input data-path="${state.contentKey}.${index}.rows.${rowIndex}.${key}" value="${esc(row[key])}" aria-label="${label}, row ${rowIndex+1}"></td>`).join('')}<td><button class="remove-row" data-action="remove-row" data-row="${rowIndex}" aria-label="Remove row ${rowIndex+1}">${icon('trash')}</button></td></tr>`).join('')}</tbody></table></div><button class="btn btn-ghost btn-small" data-action="add-row">${icon('plus')}Add a row</button></div>`;
}

function voiceOptions() {
  const voices = state.status.voices || [];
  const options = voices.map(voice => typeof voice === 'string'
    ? {value:voice,label:voice,engine:engineForVoice(voice),available:true}
    : {value:voice.id,label:voice.name || voice.id,engine:voice.engine || engineForVoice(voice.id),available:voice.available !== false});
  options.forEach(option => { if(option.engine==='kokoro' && state.status.naturalVoices?.available===false)option.available=false; });
  if(!options.some(option=>option.value===''))options.unshift({value:'',label:'Default Windows voice',engine:'windows',available:options.some(option=>option.engine==='windows'&&option.available) || !state.status.voices});
  const selected = state.project.settings.voice;
  if (selected && !options.some(option => option.value === selected)) options.push({value:selected,label:selected,engine:engineForVoice(selected),available:false});
  return options;
}

function voiceOptionsHTML() {
  const options=voiceOptions(),selected=String(state.project.settings.voice || '');
  return [['kokoro','Natural voices · offline'],['windows','Windows voices']].map(([engine,label])=>{
    const group=options.filter(option=>option.engine===engine);
    if(!group.length)return '';
    return `<optgroup label="${label}">${group.map(option=>`<option value="${esc(option.value)}" ${selected===String(option.value)?'selected':''} ${option.available?'':'disabled'}>${esc(option.label)}${option.available?'':' · not installed'}</option>`).join('')}</optgroup>`;
  }).join('');
}

function selectedVoice() {
  return voiceOptions().find(option=>String(option.value)===String(state.project.settings.voice || ''));
}

function voicePreviewHTML() {
  const selected=selectedVoice(),sample=state.voicePreview,natural=state.status.naturalVoices;
  const sampleName=sample?.name || selected?.label || 'Selected voice';
  const ready=selected?.available!==false;
  const seconds=Number(sample?.duration);
  return `<section class="voice-audition" aria-label="Listen to your narrator">
    <div class="voice-audition-heading"><div><strong>Find your voice</strong><p>Hear a short sample before you export.</p></div><button class="btn btn-secondary btn-small" data-action="listen-voice" ${state.voicePreviewBusy || !ready?'disabled':''}>${state.voicePreviewBusy?'<span class="busy-dot"></span>':icon('play')}${state.voicePreviewBusy?'Preparing sample…':'Listen to voice'}</button></div>
    <p class="voice-offline-note">Natural voices are free and work offline after setup.</p>
    ${natural?.available===false?`<div class="voice-setup-hint">${natural.message?`${esc(natural.message)} `:''}${/install\.cmd/i.test(natural.message||'')?'':'Run <strong>Install.cmd</strong> to install the natural voices.'}</div>`:''}
    ${!ready?'<p class="voice-selection-hint">This saved voice is unavailable. Choose an installed voice or finish setup with Install.cmd.</p>':''}
    <div class="voice-sample-state" aria-live="polite">${state.voicePreviewBusy?'<p class="voice-working">Generating the sample on this computer. You can keep editing.</p>':''}${state.voicePreviewError?`<p class="voice-preview-error" role="alert">${esc(state.voicePreviewError)}</p>`:''}</div>
    ${sample?`<div class="voice-player"><div class="voice-player-label"><strong>${esc(sampleName)}</strong>${Number.isFinite(seconds)&&seconds>0?`<span>${Math.round(seconds)} sec</span>`:''}</div><audio data-voice-audio controls preload="metadata" src="${safeUrl(sample.url)}" aria-label="Voice sample: ${esc(sampleName)}"></audio>${sample.text?`<details class="voice-sample-script"><summary>Sample text</summary><p>${esc(sample.text)}</p></details>`:''}</div>`:''}
  </section>`;
}

function updateVoicePreviewDOM() {
  document.querySelectorAll('[data-voice-preview]').forEach(node=>{node.innerHTML=voicePreviewHTML();});
}

function invalidateVoicePreview() {
  state.voicePreviewVersion+=1;
  state.voicePreviewController?.abort();
  state.voicePreviewController=null;
  document.querySelectorAll('[data-voice-audio]').forEach(player=>player.pause());
  state.voicePreview=null;
  state.voicePreviewError='';
  state.voicePreviewBusy=false;
  updateVoicePreviewDOM();
}

async function listenToVoice() {
  if(state.voicePreviewBusy)return;
  if(selectedVoice()?.available===false)return;
  const version=++state.voicePreviewVersion;
  const voice=String(state.project.settings.voice || ''),speechRate=Number(state.project.settings.speechRate)||0;
  const controller=new AbortController();
  state.voicePreviewController=controller;
  state.voicePreview=null;
  state.voicePreviewError='';
  state.voicePreviewBusy=true;
  updateVoicePreviewDOM();
  try{
    const sample=await api('/api/voice-preview',{method:'POST',body:JSON.stringify({voice,speechRate}),signal:controller.signal});
    if(version!==state.voicePreviewVersion)return;
    if(!sample.url || !safeUrl(sample.url))throw new Error('The narrator did not return a playable audio sample. Please try again.');
    state.voicePreview=sample;
  }catch(error){
    if(version!==state.voicePreviewVersion || error.name==='AbortError')return;
    state.voicePreviewError=error.message || 'The audio preview could not be generated. Please try again.';
  }finally{
    if(version===state.voicePreviewVersion){
      state.voicePreviewBusy=false;
      state.voicePreviewController=null;
      updateVoicePreviewDOM();
      if(state.voicePreview){
        const player=document.querySelector('[data-voice-audio]');
        if(player)player.play().catch(()=>{});
      }
    }
  }
}

function brandLogo(brand, className = 'brand-card-logo') {
  const logo = safeUrl(brand.logo);
  return `<span class="${className}">${logo ? `<img src="${logo}" alt="${esc(brand.name)} logo" loading="lazy">` : esc(brandInitials(brand))}</span>`;
}

function brandEditor() {
  const brand = currentBrand();
  if (!brand) return `<div class="panel"><div class="empty-state"><p>Add your first brand to begin.</p><button class="btn btn-primary" data-action="add-brand">${icon('plus')}Add brand</button></div></div>`;
  const index = state.project.brands.indexOf(brand), prefix = `brands.${index}`;
  return `
    <div class="brand-toolbar"><div><h2>Your companies</h2><p>${state.project.brands.length} saved</p></div><button class="btn btn-primary btn-small" data-action="add-brand">${icon('plus')}Add brand</button></div>
    <div class="brand-list" aria-label="Brand library">${state.project.brands.map(item => `<button class="brand-card ${item.id === brand.id ? 'active' : ''}" data-brand="${esc(item.id)}" aria-pressed="${item.id === brand.id}">${brandLogo(item)}<span><strong>${esc(item.name)}</strong><small>${item.enabled === false ? 'Excluded from default batch' : 'Brand variation'}</small></span></button>`).join('')}</div>
    <section class="panel">
      <div class="panel-header"><div><h2>${esc(brand.name)}</h2><p class="subtitle">A consistent identity, from first frame to last</p></div>${toggle(`${prefix}.enabled`,brand.enabled !== false,'Default batch','data-rebuild="true"')}</div>
      <div class="panel-body">
        <div class="logo-upload-row"><div class="logo-preview">${safeUrl(brand.logo) ? `<img src="${safeUrl(brand.logo)}" alt="${esc(brand.name)} logo">` : icon('image')}</div><div><label class="btn btn-secondary btn-small upload-label" for="logo-file">${icon('upload')}Replace logo</label><input type="file" id="logo-file" class="file-input" accept="image/png,image/jpeg,image/webp">${brand.logo?`<button class="btn btn-ghost btn-small" data-action="logo-colors">Use logo colors</button>`:''}<p>PNG, JPG or WebP. Logo colors are selected automatically; white and black are ignored. You can adjust them below.</p></div></div>
        ${field('Brand name',`${prefix}.name`,brand.name)}
        ${(brand.id==='lotus-insights' || brand.useSharedContent!==undefined) ? `<div class="settings-row" style="margin-bottom:18px"><div><strong>Use shared daily content</strong><p>Off preserves the separate Lotus Insights script.</p></div>${toggle(`${prefix}.useSharedContent`,brand.useSharedContent!==false,'Shared script','data-rebuild="true"')}</div>`:''}
        <div class="field-row">${colorField('Primary color',`${prefix}.primary`,brand.primary || '#144f9f')}${colorField('Accent color',`${prefix}.accent`,brand.accent || '#f3b74f')}</div>
        <div class="divider"></div>
        <div class="subheading"><h3>Closing screen</h3><button class="btn btn-ghost btn-small" data-action="preview-ending">${icon('image')}Preview ending</button></div>
        ${field('Ending design',`${prefix}.endingStyle`,brand.endingStyle,{select:[...(brand.layout==='insights'?[{value:'follow',label:'Comic follow card'}]:[]),{value:'combined',label:'Contact details + disclaimer'},{value:'contact',label:'Compact contact + disclaimer'},{value:'disclaimer',label:'Full-screen disclaimer'}]})}
        ${field('Ending minimum duration',`${prefix}.endingDuration`,brand.endingDuration || 10,{type:'number',number:true,min:5,max:180,step:1,hint:'Seconds. Allow enough time for viewers to read your disclosure.'})}
        <div class="field-row">${field('Website',`${prefix}.website`,brand.website,{placeholder:'yourwebsite.com'})}${field('Phone',`${prefix}.phone`,brand.phone,{type:'tel',placeholder:'+91 …'})}</div>
        ${field('Email',`${prefix}.email`,brand.email,{type:'email',optional:true,placeholder:'hello@yourbrand.com'})}
        ${field('Office address',`${prefix}.address`,brand.address,{textarea:true,rows:2,optional:true})}
        ${field('Disclaimer',`${prefix}.disclaimer`,brand.disclaimer,{textarea:true,rows:6,emoji:true,hint:'Your wording is used as entered. Keep required disclosures complete and easy to read.'})}
        ${brand.ending_text !== undefined || brand.layout==='insights' ? field('Closing message',`${prefix}.ending_text`,brand.ending_text || '',{textarea:true,rows:3,emoji:true,optional:true}) : ''}
        ${brand.footer_note !== undefined ? field('Footer note',`${prefix}.footer_note`,brand.footer_note || '',{textarea:true,rows:2,optional:true}) : ''}
        ${field('Social / follow message',`${prefix}.socialText`,brand.socialText || '',{optional:true,placeholder:'Subscribe for your daily market update'})}
        <div class="field-row">${field('Instagram',`${prefix}.instagram`,brand.instagram || '',{optional:true,placeholder:'@yourbrand'})}${field('Facebook',`${prefix}.facebook`,brand.facebook || '',{optional:true,placeholder:'Your page name'})}</div>
        ${field('X / Twitter',`${prefix}.twitter`,brand.twitter || '',{optional:true,placeholder:'@yourbrand'})}
        ${brand.source ? `<div class="source-note"><strong>Source reference:</strong> ${esc(typeof brand.source === 'object' ? brand.source.name || JSON.stringify(brand.source) : brand.source)}</div>` : ''}
      </div>
      <div class="panel-footer"><button class="btn btn-ghost btn-small delete-brand" data-action="delete-brand" ${state.project.brands.length===1?'disabled title="Keep at least one company in the studio."':''}>${icon('trash')}Delete brand</button><button class="btn btn-secondary btn-small" data-action="go-export">Continue to export${icon('arrow')}</button></div>
    </section>`;
}

function colorField(label,path,value) {
  const color = /^#[0-9a-f]{6}$/i.test(value) ? value : '#144f9f';
  const id = `field-${path.replaceAll('.','-')}`;
  return `<div class="field"><label for="${id}">${label}</label><div class="color-field"><input type="color" data-path="${path}" value="${esc(color)}" aria-label="Choose ${label.toLowerCase()}"><input id="${id}" type="text" data-path="${path}" value="${esc(value)}" placeholder="#144f9f" pattern="#[0-9a-fA-F]{6}" maxlength="7" aria-label="${label} hex value"></div></div>`;
}

function exportEditor() {
  const settings = state.project.settings;
  const enabledCount = activeSections().length;
  const runtimeWarnings = [];
  if (!runtimeReady(state.status.ffmpeg)) runtimeWarnings.push('The video encoder is unavailable. Run the installer to finish setting up this computer.');
  if (!runtimeReady(state.status.browser)) runtimeWarnings.push('The rendering browser is unavailable. Run the installer to finish setup.');
  return `${runtimeWarnings.map(text=>`<div class="notice">${esc(text)}</div>`).join('')}
    <section class="panel">
      <div class="panel-header"><div><h2>Make your daily set</h2><p class="subtitle">Portrait videos, ready to share</p></div><span class="badge orange">9:16 FORMAT</span></div>
      <div class="panel-body">
        <div class="subheading"><h3>Choose brands</h3><label class="checkbox-label"><input id="select-all-brands" type="checkbox" ${state.selected.size === state.project.brands.length ? 'checked' : ''}>Select all</label></div>
        <div class="export-brand-grid">${state.project.brands.map(brand=>`<label class="export-brand"><input type="checkbox" data-export-brand="${esc(brand.id)}" ${state.selected.has(brand.id)?'checked':''}>${brandLogo(brand)}<span><strong>${esc(brand.name)}</strong><small>Logo, colors & custom ending</small></span></label>`).join('')}</div>
        <div class="divider"></div><div class="subheading"><h3>Video & audio</h3></div>
        <div class="settings-row"><div><strong>Export quality</strong><p>MP4 · vertical 9:16</p></div><select class="control" data-path="settings.quality" aria-label="Export quality"><option value="720p" ${settings.quality==='720p'?'selected':''}>HD · 720 × 1280</option><option value="1080p" ${settings.quality!=='720p'?'selected':''}>Full HD · 1080 × 1920</option></select></div>
        <div class="settings-row"><div><strong>Voice narration</strong><p>Read the latest content of every included slide.</p></div>${toggle('settings.narration',settings.narration !== false,settings.narration!==false?'On':'Off','data-rebuild="true"')}</div>
        ${settings.narration !== false ? `<div class="settings-row narrator-row"><div><strong>Narrator for every video</strong><p>One selected voice for all companies in this batch</p></div><select class="control" data-path="settings.voice" aria-label="Narrator for every video">${voiceOptionsHTML()}</select></div>
        <div class="settings-row"><div><strong>Speaking pace</strong><p>Slower and clearer, or a little brisker</p></div><div><input aria-label="Speaking pace" type="range" min="-5" max="5" step="1" value="${Number(settings.speechRate)||0}" data-path="settings.speechRate" data-number="true"><span class="range-value" id="speech-rate-value">${Number(settings.speechRate)||0}</span></div></div>
        <div data-voice-preview>${voicePreviewHTML()}</div>
        <div class="settings-row"><div><strong>Read closing page aloud</strong><p>Also narrate each brand’s closing message.</p></div>${toggle('settings.readDisclaimer',!!settings.readDisclaimer,'Read aloud')}</div>` : ''}
        <div class="settings-row"><div><strong>Background music</strong><p>${settings.music?'An uploaded track is ready for this edition.':'Add an MP3 or WAV that you have permission to use.'}</p></div><label class="btn btn-secondary btn-small upload-label" for="music-file">${icon('upload')}${settings.music?'Replace music':'Upload music'}</label><input type="file" id="music-file" class="file-input" accept="audio/mpeg,audio/wav,.mp3,.wav"></div>
        ${settings.music ? `<div class="settings-row"><div><strong>Music volume</strong><p>Keep the voice clearly audible</p></div><div><input type="range" aria-label="Music volume" min="0" max="0.5" step="0.01" value="${Number(settings.musicVolume ?? 0.12)}" data-path="settings.musicVolume" data-number="true"><span class="range-value" id="music-volume-value">${Math.round(Number(settings.musicVolume??.12)*100)}%</span></div></div><button class="btn btn-ghost btn-small" data-action="clear-music">${icon('trash')}Remove background music</button>` : ''}
        <div class="speaker-note">${icon('mic')}<span>Slide timing grows to fit narration. Unchanged voice audio is reused; edited text generates new narration.</span></div>
        <div class="export-summary"><div><strong id="selected-count">${state.selected.size}</strong><small>brand videos</small></div><div><strong>${enabledCount}</strong><small>shared content slides</small></div><div><strong>${settings.narration!==false?'Auto':'Set'}</strong><small>${settings.narration!==false?'timing fits the voice':'your slide durations'}</small></div></div>
        <button class="btn btn-primary" style="width:100%" data-action="export" ${state.exporting?'disabled':''}>${icon('film')}${state.exporting?'Starting your export…':'Generate selected videos'}${icon('arrow')}</button>
      </div>
    </section>
    <section class="history-section"><div class="history-title"><h3>Export activity</h3><button class="btn btn-ghost btn-small" data-action="refresh-jobs">${icon('refresh')}Refresh</button></div><div id="jobs-container">${jobsHTML()}</div></section>
    <div class="panel" style="margin-top:17px"><div class="panel-body"><div class="subheading" style="margin-bottom:6px"><h3>Project backups</h3><label class="btn btn-secondary btn-small upload-label" for="project-file">${icon('upload')}Import project</label><input type="file" accept="application/json,.json" id="project-file" class="file-input"></div><p class="hint">Backups save your text and settings. Uploaded logos and music stay in this studio’s assets folder. Importing replaces the current edition and brand settings.</p></div></div>`;
}

function previewPanel() {
  const brand = currentBrand(), sections = brandSections(brand);
  const options = [{id:'intro',title:'Opening title'},...sections,{id:'ending',title:'Brand ending & disclaimer'}];
  return `<aside class="preview-column" aria-label="Video preview">
    <section class="panel preview-card"><div class="preview-title"><h3>${icon('image')}Live preview</h3><span class="badge neutral">9:16 · PORTRAIT</span></div>
      <select id="preview-brand" class="control preview-brand" aria-label="Preview brand">${state.project.brands.map(item=>`<option value="${esc(item.id)}" ${item.id === brand?.id?'selected':''}>${esc(item.name)}</option>`).join('')}</select>
      <div id="portrait-shell" class="portrait-shell"></div>
      <div class="preview-caption"><strong>${esc(brand?.name || 'Your brand')}</strong><span>${state.project.settings.quality === '720p' ? '720 × 1280' : '1080 × 1920'}</span></div>
      <select class="control preview-scene" id="preview-scene" aria-label="Preview slide">${options.map((item,index)=>`<option value="${esc(item.id)}" ${item.id===state.previewSection?'selected':''}>${index===0?'Intro':index===options.length-1?'Ending':String(index).padStart(2,'0')} · ${esc(item.title)}</option>`).join('')}</select>
      <p class="preview-note">Your actual video frame. Updates as you edit.</p><div id="preview-error"></div>
    </section>
  </aside>`;
}

function previewNotes() {
  const excluded = state.status.excluded || [];
  return `<div class="workspace-notes">
    <div class="edition-card"><h3>${icon('layers')}One story. Every brand.</h3><p>Edit your market update once. Every selected brand gets the same content, with its own look and closing message.</p><div class="brand-mini-list">${state.project.brands.slice(0,6).map(item=>brandLogo(item,'mini-brand')).join('')}<small>${state.project.brands.length} brands in your library</small></div></div>
    ${excluded.length ? `<details class="exclusion-note"><summary>${icon('shield').replace('aria-hidden="true"','aria-hidden="true" style="width:12px;height:12px;vertical-align:middle;margin-right:4px"')}${excluded.length} nested source ${excluded.length===1?'file':'files'} excluded</summary><p>Only top-level videos are used as source references. Videos inside subfolders are left out.</p><ul>${excluded.map(item=>`<li>${esc(typeof item==='string'?item:item.name||item.path)}</li>`).join('')}</ul></details>` : ''}
  </div>`;
}

function emojiPicker(id) {
  const emojis = ['📈','📉','📊','💹','💰','🏦','🌏','🇮🇳','🌅','☀️','🔔','📰','🔎','💡','✅','⚠️','🚀','🔥','🟢','🔴','⬆️','⬇️','↔️','👉'];
  return `<div class="emoji-picker" aria-label="Insert emoji">${emojis.map(emoji=>`<button data-insert-emoji="${emoji}" data-field="${id}" aria-label="Insert ${emoji}">${emoji}</button>`).join('')}</div>`;
}

function jobsHTML() {
  if (!state.jobs.length) return `<div class="panel empty-state">${icon('film')}<p>Your exports will appear here.<br>Choose your brands and generate your first daily set.</p></div>`;
  const cards = state.jobs.slice(0,state.historyLimit).map(job=>{
    const status = job.status || 'queued', running = ['queued','running','processing','rendering'].includes(status);
    const pct = Math.max(0,Math.min(100,Number(job.progress)||0));
    const outputs = job.outputs || [];
    return `<article class="job-card"><div class="job-header"><strong>${esc(job.title || 'Video batch')} ${job.createdAt ? `· ${esc(new Date(job.createdAt).toLocaleString('en-IN',{dateStyle:'medium',timeStyle:'short'}))}` : `· ${esc(job.id)}`}</strong><span class="badge ${status==='completed' || status==='done'?'green':status==='failed'?'red':'orange'}">${esc(status.toUpperCase())}</span></div><p>${esc(job.error || job.message || 'Preparing your videos…')}</p>${running ? `<div class="progress-track" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100" aria-label="Export progress"><div class="progress-fill" style="width:${pct}%"></div></div><div style="display:flex;align-items:center;justify-content:space-between"><span class="hint">${Math.round(pct)}% complete</span><button class="btn btn-ghost btn-small" data-cancel-job="${esc(job.id)}">Cancel export</button></div>`:''}${outputs.length ? `<div class="downloads">${job.zipUrl?`<a class="download-link download-all" href="${safeUrl(job.zipUrl)}" download>${icon('folder')}Download all videos<span>ZIP</span></a>`:''}${outputs.map(output=>`<a class="download-link" href="${safeUrl(output.url)}" download>${icon('export')}${esc(output.name || 'Download video')}<span>MP4</span></a>`).join('')}</div>`:''}${!running ? `<button class="btn btn-ghost btn-small delete-batch" data-delete-job="${esc(job.id)}">${icon('trash')}Delete batch permanently</button>`:''}</article>`;
  }).join('');
  return cards+(state.jobs.length>state.historyLimit ? `<button class="btn btn-secondary btn-small history-more" data-action="more-jobs">Show older batches (${state.jobs.length-state.historyLimit})</button>`:'');
}

function setPath(path,value) {
  const keys = path.split('.');
  let target = state.project;
  keys.slice(0,-1).forEach(key => { if (!target[key]) target[key] = {}; target=target[key]; });
  target[keys.at(-1)] = value;
}

function queueSave() {
  state.saveVersion += 1;
  clearTimeout(state.saveTimer);
  if (!state.project.date) {
    state.saveLabel='Add a date to save';
    updateSaveDOM();
    return;
  }
  state.saveLabel = 'Saving…';
  updateSaveDOM();
  state.saveTimer = setTimeout(()=>saveProject().catch(()=>{}),650);
}

async function saveProject() {
  clearTimeout(state.saveTimer);
  const version = state.saveVersion;
  try {
    // Serialize writes so an older request cannot overwrite a newer edition.
    if (state.saving) await state.saving.catch(()=>{});
    const body = JSON.stringify(state.project);
    const request = api('/api/project',{method:'PUT',body});
    state.saving = request;
    await request;
    if (state.saving===request) state.saving=null;
    if (version === state.saveVersion) { state.saveLabel='Saved locally'; updateSaveDOM(); }
  } catch(error) {
    state.saving=null;
    state.saveLabel='Not saved';
    updateSaveDOM();
    showError(`Your changes could not be saved. ${error.message}`);
    throw error;
  }
}

function updateSaveDOM() {
  const node=document.querySelector('#save-state');
  if (node) node.innerHTML=`${state.saveLabel==='Saving…'?'<span class="busy-dot"></span>':icon(state.saveLabel==='Saved locally'?'check':'info')}${esc(state.saveLabel)}`;
}

function queuePreview(delay=800) {
  clearTimeout(state.previewTimer);
  state.previewTimer=setTimeout(renderPreview,delay);
}

function selectOpeningPreview() {
  state.previewSection='intro';
  const selector=document.querySelector('#preview-scene');
  if(selector)selector.value='intro';
}

async function renderPreview() {
  if (!currentBrand()) return;
  const version=++state.previewVersion;
  if (!state.project.date) {
    state.previewBusy=false;
    state.previewError='Choose a publishing date to update the preview.';
    updatePreviewDOM();
    return;
  }
  state.previewBusy=true;
  state.previewError='';
  updatePreviewDOM();
  try {
    const result=await api('/api/preview',{method:'POST',body:JSON.stringify({project:state.project,brandId:state.brandId,sectionId:state.previewSection})});
    if (version!==state.previewVersion) return;
    if (!result.url) throw new Error('The renderer did not return an image.');
    state.previewUrl=result.url;
  } catch(error) {
    if (version!==state.previewVersion) return;
    state.previewError=error.message;
  } finally {
    if (version===state.previewVersion) { state.previewBusy=false; updatePreviewDOM(); }
  }
}

function updatePreviewDOM() {
  const shell=document.querySelector('#portrait-shell'), errorNode=document.querySelector('#preview-error');
  if (!shell) return;
  shell.innerHTML=`${state.previewUrl ? `<img src="${safeUrl(state.previewUrl)}" alt="Rendered ${esc(currentBrand()?.name)} video slide preview">` : `<div class="preview-empty">${icon('image')}<span>${state.previewBusy?'Composing your preview…':'Your video preview will appear here.'}</span></div>`}${state.previewBusy && state.previewUrl?'<div class="preview-loading"><span class="busy-dot" style="margin-right:7px"></span>Updating preview…</div>':''}`;
  if (errorNode) errorNode.innerHTML=state.previewError ? `<div class="preview-error">${esc(state.previewError)}<button class="btn btn-ghost btn-small preview-retry" data-action="refresh-preview">${icon('refresh')}Try preview again</button></div>`:'';
}

function showError(message) { state.error=message; toast(message,true); }
function toast(message,error=false) {
  const element=document.querySelector('#toast');
  element.textContent=message;
  element.className=`toast visible ${error?'error':''}`;
  clearTimeout(toast.timer);
  toast.timer=setTimeout(()=>element.classList.remove('visible'),error?7000:3500);
}

function changedInput(target) {
  if (!target.dataset.path) return;
  const value=target.type==='checkbox'?target.checked:target.dataset.optionalNumber==='true'&&target.value===''?null:target.dataset.number==='true'?Number(target.value):target.value;
  setPath(target.dataset.path,value);
  if (target.dataset.path.endsWith('.accent') && target.dataset.path.startsWith('brands.')) {
    state.project.brands[Number(target.dataset.path.split('.')[1])].secondary=value;
  }
  if(target.dataset.path==='settings.voice'){
    state.project.settings.voiceEngine=engineForVoice(value);
    invalidateVoicePreview();
  }
  if(target.dataset.path==='settings.speechRate')invalidateVoicePreview();
  if (target.dataset.path==='intro' || target.dataset.path==='title') selectOpeningPreview();
  if (target.dataset.path.endsWith('.enabled') && target.dataset.path.startsWith('brands.')) {
    const brand=state.project.brands[Number(target.dataset.path.split('.')[1])];
    if(value)state.selected.add(brand.id);else state.selected.delete(brand.id);
  }
  if (target.id) { const count=document.querySelector(`[data-count-for="${target.id}"]`);if(count)count.textContent=`${String(value).length} characters`; }
  if (target.type==='color' || target.dataset.path.endsWith('.primary') || target.dataset.path.endsWith('.accent')) {
    document.querySelectorAll(`[data-path="${target.dataset.path}"]`).forEach(sibling=>{ if(sibling!==target && (sibling.type!=='color' || /^#[0-9a-f]{6}$/i.test(value)))sibling.value=value; });
  }
  if (target.dataset.path==='settings.speechRate') { const node=document.querySelector('#speech-rate-value');if(node)node.textContent=value; }
  if (target.dataset.path==='settings.musicVolume') { const node=document.querySelector('#music-volume-value');if(node)node.textContent=`${Math.round(value*100)}%`; }
  if (target.type==='color' && target.closest('.style-color-row')) {
    const row=target.closest('.style-color-row');
    row.querySelector('.style-color-status').textContent=value;
    row.querySelector('[data-style-color-reset]').disabled=false;
  }
  queueSave();
  queuePreview();
}

document.querySelector('#app').addEventListener('toggle',event=>{
  if(event.target.matches('.text-style-editor')){state.textStyleOpen=event.target.open;return;}
  if (!event.target.matches('.intro-editor')) return;
  const opening=event.target.open && !state.introOpen;
  state.introOpen=event.target.open;
  if (opening) { selectOpeningPreview(); queuePreview(0); }
},true);

document.querySelector('#app').addEventListener('input',event=>{
  if (event.target.dataset.path && !['checkbox','file'].includes(event.target.type) && event.target.tagName!=='SELECT') changedInput(event.target);
});

document.querySelector('#app').addEventListener('change',async event=>{
  const target=event.target;
  try {
    if (target.dataset.path && (target.type==='checkbox'||target.tagName==='SELECT')) changedInput(target);
    if (target.dataset.rebuild) render();
    if (target.id==='preview-brand') {
      const showingIntro=state.previewSection==='intro';
      state.brandId=target.value;state.previewUrl='';
      if(state.tab==='content') {state.contentKey=currentBrand()?.useSharedContent===false&&state.project.insightsSections?'insightsSections':'sections';state.sectionId=currentSections()[0]?.id;state.previewSection=showingIntro?'intro':state.sectionId||'intro';}
      render();queuePreview(0);
    }
    if (target.id==='script-select') {
      state.contentKey=target.value;state.sectionId=currentSections()[0]?.id;state.previewSection=state.sectionId||'intro';
      const matching=state.project.brands.find(brand=>target.value==='insightsSections'?brand.useSharedContent===false:brand.useSharedContent!==false);
      if(matching)state.brandId=matching.id;
      state.previewUrl='';render();queuePreview(0);
    }
    if (target.id==='preview-scene') {state.previewSection=target.value;queuePreview(0);}
    if (target.dataset.exportBrand) {
      if(target.checked)state.selected.add(target.dataset.exportBrand);else state.selected.delete(target.dataset.exportBrand);
      updateSelectionDOM();
    }
    if (target.id==='select-all-brands') {state.selected=new Set(target.checked?state.project.brands.map(brand=>brand.id):[]);render();}
    if (target.id==='logo-file' && target.files[0]) {
      const file=target.files[0];
      if (file.size>20*1024*1024) throw new Error('Please choose a logo smaller than 20 MB.');
      const brand=currentBrand(),form=new FormData();form.append('file',file);
      toast('Uploading your logo…');
      const result=await api('/api/upload',{method:'POST',body:form});
      brand.logo=result.url;
      if(result.palette){brand.primary=result.palette.primary;brand.secondary=result.palette.secondary;brand.accent=result.palette.accent;}
      queueSave();render();queuePreview(0);toast(result.palette?'Logo and brand colors updated.':'Logo updated. Choose your brand colors below.');
    }
    if (target.id==='music-file' && target.files[0]) {
      const file=target.files[0];if(file.size>29*1024*1024)throw new Error('Please choose a music file smaller than 29 MB.');
      const form=new FormData();form.append('file',file);toast('Uploading your music…');
      const result=await api('/api/upload',{method:'POST',body:form});
      state.project.settings.music=result.url;state.project.settings.musicVolume??=.12;queueSave();render();toast('Background music added.');
    }
    if (target.id==='project-file' && target.files[0]) {
      const project=normalizeProject(JSON.parse(await target.files[0].text()));
      clearTimeout(state.saveTimer);
      if(state.saving)await state.saving.catch(()=>{});
      await api('/api/project',{method:'PUT',body:JSON.stringify(project)});
      state.project=project;state.contentKey='sections';state.brandId=project.brands[0]?.id;state.sectionId=project.sections[0]?.id;state.previewSection=state.sectionId||'intro';state.previewUrl='';state.selected=new Set(project.brands.filter(brand=>brand.enabled!==false).map(brand=>brand.id));
      invalidateVoicePreview();
      render();queuePreview(0);toast('Project imported. Your edition is ready to edit.');
    }
  } catch(error) {showError(error.message);render();}
});

function updateSelectionDOM() {
  const count=document.querySelector('#selected-count'),all=document.querySelector('#select-all-brands');
  if(count)count.textContent=state.selected.size;
  if(all){all.checked=state.selected.size===state.project.brands.length;all.indeterminate=state.selected.size>0&&!all.checked;}
}

document.querySelector('#app').addEventListener('click',async event=>{
  const target=event.target.closest('button,[data-tab],[data-section],[data-brand]');
  if(!target)return;
  try {
    if(target.dataset.tab){
      state.tab=target.dataset.tab;state.emojiField=null;
      if(state.tab==='brands')state.previewSection='ending';
      if(state.tab==='content'){
        state.contentKey=currentBrand()?.useSharedContent===false&&state.project.insightsSections?'insightsSections':'sections';
        state.sectionId=currentSection()?.id;state.previewSection=state.sectionId||'intro';
      }
      render();queuePreview(0);return;
    }
    if(target.dataset.section){state.sectionId=target.dataset.section;state.previewSection=target.dataset.section;state.emojiField=null;render();queuePreview(0);return;}
    if(target.dataset.brand){state.brandId=target.dataset.brand;state.previewSection='ending';state.previewUrl='';render();queuePreview(0);return;}
    if(target.dataset.insertEmoji){
      const textarea=document.getElementById(target.dataset.field);
      if(textarea){const start=textarea.selectionStart,end=textarea.selectionEnd;textarea.setRangeText(target.dataset.insertEmoji,start,end,'end');changedInput(textarea);textarea.focus();}
      return;
    }
    if(target.dataset.cancelJob){await api(`/api/jobs/${encodeURIComponent(target.dataset.cancelJob)}/cancel`,{method:'POST'});await refreshJobs();toast('Cancellation requested.');return;}
    if(target.dataset.styleColorReset){setPath(target.dataset.styleColorReset,'auto');queueSave();render();queuePreview();return;}
    if(target.dataset.deleteJob){
      const job=state.jobs.find(item=>item.id===target.dataset.deleteJob);
      if(!job)return;
      if(!window.confirm(`Permanently delete this batch (${job.id})?\n\nAll videos, the ZIP download, and export files in this batch will be removed from this computer. This cannot be undone.`))return;
      target.disabled=true;
      await api(`/api/jobs/${encodeURIComponent(job.id)}`,{method:'DELETE'});
      await refreshJobs();toast('Batch permanently deleted.');return;
    }
    switch(target.dataset.action){
      case 'reload':location.reload();break;
      case 'listen-voice':await listenToVoice();break;
      case 'backup':{
        const url=URL.createObjectURL(new Blob([JSON.stringify(state.project,null,2)],{type:'application/json'}));
        const anchor=document.createElement('a');anchor.href=url;anchor.download=`tarkash-project-${state.project.date||'backup'}.json`;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),5000);toast('Project backup downloaded.');break;
      }
      case 'go-export':state.tab='export';state.emojiField=null;render();refreshJobs();break;
      case 'dismiss-error':state.error='';render();break;
      case 'refresh-preview':queuePreview(0);break;
      case 'preview-intro':state.previewSection='intro';render();queuePreview(0);break;
      case 'preview-ending':state.previewSection='ending';render();queuePreview(0);break;
      case 'clear-music':state.project.settings.music='';queueSave();render();break;
      case 'logo-colors':{
        const brand=currentBrand(),result=await api('/api/logo-palette',{method:'POST',body:JSON.stringify({url:brand.logo})});
        if(!result.palette){toast('No colored pixels found in this logo. Choose colors below.');break;}
        Object.assign(brand,result.palette);queueSave();render();queuePreview(0);toast('Brand colors selected from the logo.');break;
      }
      case 'next-section':{
        const sections=currentSections(),index=sections.indexOf(currentSection());
        if(index===sections.length-1){state.tab='brands';state.previewSection='ending';}
        else{state.sectionId=sections[index+1].id;state.previewSection=state.sectionId;}
        state.emojiField=null;render();queuePreview(0);break;
      }
      case 'emoji':{
        const textarea=document.getElementById(target.dataset.field);
        const cursor=textarea?{start:textarea.selectionStart,end:textarea.selectionEnd}:null;
        state.emojiField=state.emojiField===target.dataset.field?null:target.dataset.field;
        render();
        const rebuilt=document.getElementById(target.dataset.field);
        if(rebuilt&&cursor){rebuilt.focus();rebuilt.setSelectionRange(cursor.start,cursor.end);}
        break;
      }
      case 'add-row':currentSection().rows.push({metric:'',nifty:'',sensex:'',bankNifty:''});queueSave();render();queuePreview();break;
      case 'remove-row':currentSection().rows.splice(Number(target.dataset.row),1);queueSave();render();queuePreview();break;
      case 'add-brand':{
        const brand={id:`brand-${Date.now().toString(36)}`,name:'New brand',primary:'#1456a0',accent:'#e8aa57',logo:'',website:'',phone:'',address:'',email:'',disclaimer:currentBrand()?.disclaimer||'',endingStyle:'combined',enabled:true,source:'Custom brand'};
        state.project.brands.push(brand);state.brandId=brand.id;state.selected.add(brand.id);state.previewSection='ending';queueSave();render();queuePreview(0);break;
      }
      case 'delete-brand':{
        const brand=currentBrand();
        if(!brand || state.project.brands.length<=1)break;
        if(!window.confirm(`Delete ${brand.name} from your saved companies?\n\nIt will no longer be available for future exports. Videos already generated for this company remain in Export activity.`))break;
        const index=state.project.brands.indexOf(brand);
        clearTimeout(state.previewTimer);
        state.previewVersion++;
        state.project.brands.splice(index,1);
        state.selected.delete(brand.id);
        state.brandId=state.project.brands[Math.min(index,state.project.brands.length-1)].id;
        state.previewSection='ending';state.previewUrl='';state.previewError='';
        queueSave();render();queuePreview(0);toast(`${brand.name} deleted from your company library.`);break;
      }
      case 'refresh-jobs':await refreshJobs();break;
      case 'more-jobs':state.historyLimit+=8;document.querySelector('#jobs-container').innerHTML=jobsHTML();break;
      case 'export':await startExport();break;
    }
  }catch(error){showError(error.message);render();}
});

async function startExport() {
  if(state.exporting)return;
  if(!state.selected.size)throw new Error('Choose at least one brand to generate a video.');
  if(!activeSections().length)throw new Error('Include at least one content slide before exporting.');
  if(!state.project.date)throw new Error('Add a publishing date in Daily content before exporting.');
  const invalid=state.project.brands.find(brand=>state.selected.has(brand.id)&&(!/^#[\da-f]{6}$/i.test(brand.primary)||!/^#[\da-f]{6}$/i.test(brand.accent)));
  if(invalid)throw new Error(`Check ${invalid.name}’s colors. Enter a six-digit hex color such as #1456a0.`);
  state.exporting=true;state.tab='export';state.error='';render();
  try{
    await saveProject();
    const result=await api('/api/jobs',{method:'POST',body:JSON.stringify({project:state.project,brandIds:[...state.selected]})});
    if(!result.id)throw new Error('The renderer did not return an export identifier.');
    state.jobs.unshift({id:result.id,status:'queued',progress:0,message:'Your videos are queued for rendering.',outputs:[]});
    toast('Your video batch is on its way.');
    await refreshJobs();
    pollJobs();
  }finally{state.exporting=false;render();}
}

async function refreshJobs() {
  const result=await api('/api/jobs');
  state.jobs=Array.isArray(result)?result:result.jobs||[];
  const node=document.querySelector('#jobs-container');if(node)node.innerHTML=jobsHTML();
}

async function pollJobs() {
  clearTimeout(state.pollTimer);
  const pending=state.jobs.filter(job=>['queued','running','processing','rendering'].includes(job.status));
  if(!pending.length)return;
  const results=await Promise.allSettled(pending.map(job=>api(`/api/jobs/${encodeURIComponent(job.id)}`)));
  results.forEach((result,index)=>{
    if(result.status==='fulfilled'){
      const jobIndex=state.jobs.findIndex(job=>job.id===pending[index].id);
      if(jobIndex>=0)state.jobs[jobIndex]=result.value;
      if(['completed','done'].includes(result.value.status))toast('Your videos are ready to download.');
      if(result.value.status==='failed')toast(result.value.error||'The video export could not finish.',true);
    }
  });
  const node=document.querySelector('#jobs-container');if(node)node.innerHTML=jobsHTML();
  if(state.jobs.some(job=>['queued','running','processing','rendering'].includes(job.status)))state.pollTimer=setTimeout(pollJobs,1800);
}

window.addEventListener('beforeunload',event=>{
  if(state.project && state.saveLabel!=='Saved locally'){event.preventDefault();event.returnValue='';}
});

init();
