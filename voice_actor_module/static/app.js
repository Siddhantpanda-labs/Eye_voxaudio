/* ============================================
   VoxStudio — Application Logic
   ============================================ */

const EMOTION_ICONS = {
    angry: '😡', sad: '😢', happy: '😄', calm: '😌',
    curious: '🤔', excited: '🤩', threatening: '💀',
    sarcastic: '😏', romantic: '💕', dramatic: '🎭',
    whisper: '🤫', default: '🎤'
};

// ---- State ----
let currentAudioUrl = null;
const sessionHistory = [];

// ---- DOM ----
const scriptInput = document.getElementById('script');
const modeScriptBtn = document.getElementById('mode-script-btn');
const modeConvBtn = document.getElementById('mode-conv-btn');
const scriptModeContainer = document.getElementById('script-mode-container');
const convModeContainer = document.getElementById('conv-mode-container');
const convLinesContainer = document.getElementById('conv-lines-container');
const addConvLineBtn = document.getElementById('add-conv-line-btn');
const convLineTemplate = document.getElementById('conv-line-template');

let currentMode = 'script';
const engineSelect = document.getElementById('engine');
const cbVoiceGroup = document.getElementById('cb-voice-group');
const cbVoiceSelect = document.getElementById('cb-voice');
const cbUploadSection = document.getElementById('cb-upload-section');
const cbDeleteSection = document.getElementById('cb-delete-section');
const cbNewVoiceName = document.getElementById('cb-new-voice-name');
const cbSaveVoiceBtn = document.getElementById('cb-save-voice-btn');
const cbDeleteVoiceBtn = document.getElementById('cb-delete-voice-btn');
const refAudioInput = document.getElementById('ref-audio');
const voiceGroup = document.getElementById('voice-group');
const voiceSelect = document.getElementById('voice');
const toneSelect = document.getElementById('tone');
const targetLanguageSelect = document.getElementById('target-language');
const fxCheckbox = document.getElementById('apply-fx');
const hesitationSlider = document.getElementById('hesitation');
const hesitationVal = document.getElementById('hesitation-val');
const breathinessSlider = document.getElementById('breathiness');
const breathinessVal = document.getElementById('breathiness-val');
const elControls = document.getElementById('el-controls');
const elStabilitySlider = document.getElementById('el-stability');
const elStabilityVal = document.getElementById('el-stability-val');
const elSimilaritySlider = document.getElementById('el-similarity');
const elSimilarityVal = document.getElementById('el-similarity-val');
const elStyleSlider = document.getElementById('el-style');
const elStyleVal = document.getElementById('el-style-val');
const elBoostCheckbox = document.getElementById('el-boost');
const cbControls = document.getElementById('cb-controls');
const cbExaggerationSlider = document.getElementById('cb-exaggeration');
const cbExaggerationVal = document.getElementById('cb-exaggeration-val');
const cbCfgWeightSlider = document.getElementById('cb-cfg-weight');
const cbCfgWeightVal = document.getElementById('cb-cfg-weight-val');
const cbTemperatureSlider = document.getElementById('cb-temperature');
const cbTemperatureVal = document.getElementById('cb-temperature-val');
const cbRepPenaltySlider = document.getElementById('cb-rep-penalty');
const cbRepPenaltyVal = document.getElementById('cb-rep-penalty-val');
const generateBtn = document.getElementById('generate-btn');
const outputCard = document.getElementById('current-output');
const emptyState = document.getElementById('empty-state');
const intentBadges = document.getElementById('intent-badges');
const refinedScript = document.getElementById('refined-script');
const audioPlayer = document.getElementById('audio-player');
const blobCanvas = document.getElementById('blob-canvas');
const playBtn = document.getElementById('play-btn');
const playIcon = document.getElementById('play-icon');
const pauseIcon = document.getElementById('pause-icon');
const timeDisplay = document.getElementById('time-display');
const downloadBtn = document.getElementById('download-btn');
const historyList = document.getElementById('history-list');
const charCount = document.getElementById('char-count');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');

// ---- Init: Fetch Voices ----
async function loadVoices() {
    try {
        const resp = await fetch('/api/voices');
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail);

        voiceSelect.innerHTML = '';
        data.voices.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v.voice_id;
            const desc = v.labels?.description || v.labels?.accent || v.category || '';
            opt.textContent = `${v.name}${desc ? ' — ' + desc : ''}`;
            voiceSelect.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load voices:', e);
        voiceSelect.innerHTML = `
            <option value="pNInz6obpgDQGcFmaJgB">Adam</option>
            <option value="21m00Tcm4TlvDq8ikWAM">Rachel</option>
            <option value="ErXwobaYiN019PkySvjV">Antoni</option>
        `;
    }
}
loadVoices();

async function loadCbVoices() {
    try {
        const resp = await fetch('/api/chatterbox/voices');
        const data = await resp.json();
        
        cbVoiceSelect.innerHTML = '<option value="">-- Upload New Reference --</option>';
        data.voices.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v.id;
            opt.textContent = v.name;
            cbVoiceSelect.appendChild(opt);
        });
        updateCbVoiceUI();
    } catch (e) {
        console.error('Failed to load CB voices:', e);
    }
}
loadCbVoices();

function updateCbVoiceUI() {
    if (cbVoiceSelect.value) {
        cbUploadSection.style.display = 'none';
        cbDeleteSection.style.display = 'block';
    } else {
        cbUploadSection.style.display = 'block';
        cbDeleteSection.style.display = 'none';
    }
}
cbVoiceSelect.addEventListener('change', updateCbVoiceUI);

// ---- Mode Switching ----
modeScriptBtn.addEventListener('click', () => {
    currentMode = 'script';
    modeScriptBtn.style.background = 'var(--bg-elevated)';
    modeScriptBtn.style.color = 'var(--text-primary)';
    modeConvBtn.style.background = 'transparent';
    modeConvBtn.style.color = 'var(--text-muted)';
    
    scriptModeContainer.style.display = 'block';
    convModeContainer.style.display = 'none';
});

modeConvBtn.addEventListener('click', () => {
    currentMode = 'conversation';
    modeConvBtn.style.background = 'var(--bg-elevated)';
    modeConvBtn.style.color = 'var(--text-primary)';
    modeScriptBtn.style.background = 'transparent';
    modeScriptBtn.style.color = 'var(--text-muted)';
    
    scriptModeContainer.style.display = 'none';
    convModeContainer.style.display = 'block';
    
    if (convLinesContainer.children.length === 0) {
        addConvLine();
    }
});

// ---- Conversation Logic ----
function addConvLine() {
    const clone = convLineTemplate.content.cloneNode(true);
    const lineEl = clone.querySelector('.conv-line');
    const engineSelect = clone.querySelector('.conv-engine');
    const voiceSelect = clone.querySelector('.conv-voice');
    const fishVoiceInput = clone.querySelector('.conv-fish-voice');
    const removeBtn = clone.querySelector('.remove-line-btn');
    
    function populateVoices() {
        voiceSelect.innerHTML = '';
        if (engineSelect.value === 'elevenlabs') {
            Array.from(document.getElementById('voice').options).forEach(o => {
                const opt = document.createElement('option');
                opt.value = o.value;
                opt.textContent = o.textContent;
                voiceSelect.appendChild(opt);
            });
        } else {
            Array.from(document.getElementById('cb-voice').options).forEach(o => {
                if (o.value) { // Skip the upload option
                    const opt = document.createElement('option');
                    opt.value = o.value;
                    opt.textContent = o.textContent;
                    voiceSelect.appendChild(opt);
                }
            });
        }
    }
    
    engineSelect.addEventListener('change', populateVoices);
    populateVoices(); // init
    
    removeBtn.addEventListener('click', () => {
        lineEl.remove();
    });
    
    convLinesContainer.appendChild(clone);
}

addConvLineBtn.addEventListener('click', addConvLine);

cbSaveVoiceBtn.addEventListener('click', async () => {
    const name = cbNewVoiceName.value.trim();
    if (!name) return alert("Please enter a voice name");
    if (refAudioInput.files.length === 0) return alert("Please select an audio file");
    
    cbSaveVoiceBtn.disabled = true;
    cbSaveVoiceBtn.textContent = "Saving...";
    try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('ref_audio', refAudioInput.files[0]);
        
        const resp = await fetch('/api/chatterbox/voices', {
            method: 'POST',
            body: formData
        });
        if (!resp.ok) throw new Error(await resp.text());
        const data = await resp.json();
        
        await loadCbVoices();
        cbVoiceSelect.value = data.id;
        updateCbVoiceUI();
        
        cbNewVoiceName.value = '';
        refAudioInput.value = '';
        alert("Voice saved successfully!");
    } catch(e) {
        alert("Error saving voice: " + e.message);
    } finally {
        cbSaveVoiceBtn.disabled = false;
        cbSaveVoiceBtn.textContent = "Save";
    }
});

cbDeleteVoiceBtn.addEventListener('click', async () => {
    const voiceId = cbVoiceSelect.value;
    if (!voiceId) return;
    if (!confirm("Delete this saved voice?")) return;
    
    try {
        const resp = await fetch(`/api/chatterbox/voices/${voiceId}`, { method: 'DELETE' });
        if (!resp.ok) throw new Error(await resp.text());
        
        await loadCbVoices();
        cbVoiceSelect.value = '';
        updateCbVoiceUI();
    } catch(e) {
        alert("Error deleting voice: " + e.message);
    }
});

// ---- Expression Tag Palette ----
document.querySelectorAll('.tag-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tag = btn.dataset.tag;
        const start = scriptInput.selectionStart;
        const end = scriptInput.selectionEnd;
        const before = scriptInput.value.substring(0, start);
        const after = scriptInput.value.substring(end);
        scriptInput.value = before + tag + after;
        scriptInput.selectionStart = scriptInput.selectionEnd = start + tag.length;
        scriptInput.focus();
        charCount.textContent = scriptInput.value.length;
    });
});

// ---- Char count ----
scriptInput.addEventListener('input', () => {
    charCount.textContent = scriptInput.value.length;
});

// ---- Director Sliders ----
hesitationSlider.addEventListener('input', () => {
    hesitationVal.textContent = `${hesitationSlider.value}%`;
});

breathinessSlider.addEventListener('input', () => {
    breathinessVal.textContent = `${breathinessSlider.value}%`;
});

// ---- ElevenLabs Sliders ----
elStabilitySlider.addEventListener('input', () => {
    elStabilityVal.textContent = (elStabilitySlider.value / 100).toFixed(2);
});

elSimilaritySlider.addEventListener('input', () => {
    elSimilarityVal.textContent = (elSimilaritySlider.value / 100).toFixed(2);
});

elStyleSlider.addEventListener('input', () => {
    elStyleVal.textContent = (elStyleSlider.value / 100).toFixed(2);
});

// ---- Engine Toggle ----
engineSelect.addEventListener('change', () => {
    const isChatterbox = engineSelect.value === 'chatterbox';
    cbVoiceGroup.style.display = isChatterbox ? 'flex' : 'none';
    voiceGroup.style.display = isChatterbox ? 'none' : 'flex';
    elControls.style.display = isChatterbox ? 'none' : 'flex';
    cbControls.style.display = isChatterbox ? 'flex' : 'none';
});
engineSelect.dispatchEvent(new Event('change'));

// ---- Chatterbox Sliders ----
cbExaggerationSlider.addEventListener('input', () => {
    cbExaggerationVal.textContent = (cbExaggerationSlider.value / 100).toFixed(2);
});

cbCfgWeightSlider.addEventListener('input', () => {
    cbCfgWeightVal.textContent = (cbCfgWeightSlider.value / 100).toFixed(2);
});

cbTemperatureSlider.addEventListener('input', () => {
    cbTemperatureVal.textContent = (cbTemperatureSlider.value / 100).toFixed(2);
});

cbRepPenaltySlider.addEventListener('input', () => {
    cbRepPenaltyVal.textContent = (cbRepPenaltySlider.value / 100).toFixed(2);
});

// ---- Audio Visualizer State ----
let audioCtx = null;
let analyser = null;
let sourceNode = null;
let freqData = null;
let visAnimId = null;

const BAR_COUNT = 64;
const BAR_GAP = 4;
const MIN_BAR_HEIGHT = 6;
const MAX_BAR_HEIGHT = 160;

// Wide gradient: Cyan → Blue → Indigo → Violet → Magenta → Pink → Coral → Amber (Desaturated)
const COLOR_STOPS = [
    { pos: 0.0, h: 185, s: 70, l: 60 },   // cyan
    { pos: 0.15, h: 210, s: 65, l: 58 },   // sky blue
    { pos: 0.3, h: 240, s: 60, l: 65 },   // indigo
    { pos: 0.45, h: 270, s: 55, l: 60 },   // violet
    { pos: 0.6, h: 300, s: 60, l: 65 },   // magenta
    { pos: 0.75, h: 330, s: 65, l: 65 },   // pink
    { pos: 0.9, h: 15, s: 65, l: 60 },   // coral
    { pos: 1.0, h: 40, s: 70, l: 60 },   // amber
];

function lerpColor(t) {
    t = Math.max(0, Math.min(1, t));
    let a = COLOR_STOPS[0], b = COLOR_STOPS[1];
    for (let i = 0; i < COLOR_STOPS.length - 1; i++) {
        if (t >= COLOR_STOPS[i].pos && t <= COLOR_STOPS[i + 1].pos) {
            a = COLOR_STOPS[i];
            b = COLOR_STOPS[i + 1];
            break;
        }
    }
    const local = (t - a.pos) / (b.pos - a.pos || 1);
    const h = a.h + (b.h - a.h) * local;
    const s = a.s + (b.s - a.s) * local;
    const l = a.l + (b.l - a.l) * local;
    return `hsl(${h}, ${s}%, ${l}%)`;
}

function initAudioContext() {
    if (audioCtx) return;
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.8;
    freqData = new Uint8Array(analyser.frequencyBinCount);
}

function connectAudioSource() {
    if (sourceNode) { sourceNode.disconnect(); sourceNode = null; }
    initAudioContext();
    sourceNode = audioCtx.createMediaElementSource(audioPlayer);
    sourceNode.connect(analyser);
    analyser.connect(audioCtx.destination);
}

function renderVisualizer(timestamp) {
    const ctx = blobCanvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = blobCanvas.clientWidth;
    const h = blobCanvas.clientHeight;

    if (blobCanvas.width !== w * dpr || blobCanvas.height !== h * dpr) {
        blobCanvas.width = w * dpr;
        blobCanvas.height = h * dpr;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const isPlaying = !audioPlayer.paused;
    if (isPlaying && analyser) {
        analyser.getByteFrequencyData(freqData);
    }

    const totalBarWidth = (w - 60) / BAR_COUNT;
    const barWidth = totalBarWidth - BAR_GAP;
    const startX = 30 + (totalBarWidth / 2);
    const cy = h / 2;
    const time = timestamp * 0.002;

    // Draw bars
    for (let i = 0; i < BAR_COUNT; i++) {
        let freqVal = 0;
        if (isPlaying && freqData) {
            // Map bar index to frequency bin, focusing on the lower/mid spectrum for voice
            const binIdx = Math.floor((i / BAR_COUNT) * (freqData.length * 0.5));
            freqVal = freqData[binIdx] / 255;
        }

        // Idle animation: smooth cascading sine wave with taller amplitude
        const idlePulse = (Math.sin(time + i * 0.15) * 0.5 + 0.5) * 35 + MIN_BAR_HEIGHT;

        // Active audio height
        const activeHeight = freqVal * MAX_BAR_HEIGHT;

        // Combine idle and active heights
        let barHeight = Math.max(MIN_BAR_HEIGHT, idlePulse + activeHeight);

        // Add a slight secondary wobble
        barHeight *= (1 + Math.sin(time * 0.8 + i * 0.3) * 0.05);

        const x = startX + i * totalBarWidth - (barWidth / 2);
        const y = cy - barHeight / 2;

        // Color gradient across the canvas width
        const t = i / (BAR_COUNT - 1);
        const color = lerpColor(t);

        // Draw rounded rectangle bar
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.roundRect(x, y, Math.max(2, barWidth), barHeight, barWidth / 2);
        ctx.fill();

        // Add glow when active
        if (freqVal > 0.2) {
            ctx.shadowBlur = 10 + freqVal * 20;
            ctx.shadowColor = color;
            ctx.fill();
            ctx.shadowBlur = 0; // reset
        }
    }

    visAnimId = requestAnimationFrame(renderVisualizer);
}

function startVisualizerAnimation() {
    if (visAnimId) return;
    visAnimId = requestAnimationFrame(renderVisualizer);
}

// ---- Init visualizer ----
startVisualizerAnimation();

// ============================================
//  Generate
// ============================================

generateBtn.addEventListener('click', async () => {
    let endpoint = '/api/synthesize';
    let reqBody = null;
    let reqHeaders = {};
    let textToLog = "";

    if (currentMode === 'script') {
        const text = scriptInput.value.trim();
        if (!text) return;
        textToLog = text;

        const formData = new FormData();
        formData.append('text', text);
        formData.append('engine', engineSelect.value);
        formData.append('voice_id', voiceSelect.value);
        formData.append('tone', toneSelect.value);
        formData.append('target_language', targetLanguageSelect.value);
        formData.append('translate_text', true);
        formData.append('apply_fx', fxCheckbox.checked);
        formData.append('hesitation', hesitationSlider.value);
        formData.append('breathiness', breathinessSlider.value);
        
        if (engineSelect.value === 'elevenlabs') {
            formData.append('el_stability', (elStabilitySlider.value / 100).toFixed(2));
            formData.append('el_similarity', (elSimilaritySlider.value / 100).toFixed(2));
            formData.append('el_style', (elStyleSlider.value / 100).toFixed(2));
            formData.append('el_boost', elBoostCheckbox.checked);
        }

        if (engineSelect.value === 'chatterbox') {
            if (cbVoiceSelect.value) {
                formData.append('cb_voice_id', cbVoiceSelect.value);
            } else if (refAudioInput.files.length > 0) {
                formData.append('ref_audio', refAudioInput.files[0]);
            }
            formData.append('cb_exaggeration', (cbExaggerationSlider.value / 100).toFixed(2));
            formData.append('cb_cfg_weight', (cbCfgWeightSlider.value / 100).toFixed(2));
            formData.append('cb_temperature', (cbTemperatureSlider.value / 100).toFixed(2));
            formData.append('cb_repetition_penalty', (cbRepPenaltySlider.value / 100).toFixed(2));
        }
        reqBody = formData;
    } else {
        const lines = [];
        const lineEls = convLinesContainer.querySelectorAll('.conv-line');
        for (let el of lineEls) {
            const txt = el.querySelector('.conv-text').value.trim();
            if (txt) {
                lines.push({
                    text: txt,
                    engine: el.querySelector('.conv-engine').value,
                    voice_id: el.querySelector('.conv-voice').value,
                    target_language: el.querySelector('.conv-language').value
                });
            }
        }
        if (lines.length === 0) return alert('Add at least one line of dialogue.');
        
        endpoint = '/api/synthesize_conversation';
        reqBody = JSON.stringify({ 
            lines: lines,
            apply_fx: fxCheckbox.checked
        });
        reqHeaders = { 'Content-Type': 'application/json' };
        textToLog = "Conversation Mode: " + lines.length + " lines";
    }

    setStatus('busy', 'Generating...');
    generateBtn.disabled = true;
    generateBtn.innerHTML = `<span class="loader-bars" style="height:18px;gap:2px"><span></span><span></span><span></span></span> Directing...`;
    outputCard.classList.add('hidden');
    emptyState.classList.add('hidden');

    try {
        const fetchOptions = {
            method: 'POST',
            body: reqBody
        };
        if (Object.keys(reqHeaders).length > 0) {
            fetchOptions.headers = reqHeaders;
        }
        
        const resp = await fetch(endpoint, fetchOptions);

        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail);

        renderOutput(data);
        addToHistory(data, textToLog);
        setStatus('ready', 'Ready');

    } catch (err) {
        alert('Error: ' + err.message);
        setStatus('ready', 'Error');
    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Generate Take`;
    }
});

// ---- Render Output ----
function renderOutput(data) {
    const intent = data.intent;
    const emotion = intent.emotion || 'calm';
    const emotionIcon = EMOTION_ICONS[emotion] || EMOTION_ICONS.default;

    intentBadges.innerHTML = `
        <div class="badge lang"><span class="label">Lang</span> ${intent.language || 'English'}</div>
        <div class="badge emotion"><span class="label">Emotion</span> ${emotionIcon} ${emotion}</div>
        <div class="badge style"><span class="label">Style</span> ${intent.style}</div>
        <div class="badge metric"><span class="label">Intensity</span> ${intent.intensity}</div>
        <div class="badge metric"><span class="label">Pacing</span> ${intent.pacing}x</div>
    `;

    refinedScript.innerHTML = `<strong>Refined Script</strong>"${intent.refined_text || data.conditioned_text}"`;

    currentAudioUrl = data.audio_url;
    audioPlayer.src = `${data.audio_url}?t=${Date.now()}`;

    outputCard.classList.remove('hidden');

    // Connect audio to analyser and auto-play
    audioPlayer.addEventListener('canplaythrough', () => {
        try {
            if (!sourceNode) connectAudioSource();
            audioPlayer.play();
            showPauseIcon();
        } catch (e) {
            console.warn('Auto-play blocked, click play:', e);
        }
    }, { once: true });

    audioPlayer.load();
}

// ---- Custom Playback ----
playBtn.addEventListener('click', () => {
    if (!sourceNode) {
        try { connectAudioSource(); } catch (e) { /* already connected */ }
    }
    if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();

    if (audioPlayer.paused) {
        audioPlayer.play();
        showPauseIcon();
    } else {
        audioPlayer.pause();
        showPlayIcon();
    }
});

audioPlayer.addEventListener('ended', showPlayIcon);

audioPlayer.addEventListener('timeupdate', () => {
    timeDisplay.textContent = `${fmt(audioPlayer.currentTime)} / ${fmt(audioPlayer.duration)}`;
});

function showPlayIcon() { playIcon.classList.remove('hidden'); pauseIcon.classList.add('hidden'); }
function showPauseIcon() { playIcon.classList.add('hidden'); pauseIcon.classList.remove('hidden'); }

function fmt(s) {
    if (isNaN(s)) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
}

// ---- Download ----
downloadBtn.addEventListener('click', () => {
    if (!currentAudioUrl) return;
    const a = document.createElement('a');
    a.href = currentAudioUrl;
    a.download = 'voxstudio_take.mp3';
    a.click();
});

// ---- History ----
function addToHistory(data, originalText) {
    const emotion = data.intent.emotion || 'calm';
    const icon = EMOTION_ICONS[emotion] || EMOTION_ICONS.default;
    const entry = { ...data, originalText, icon };
    sessionHistory.unshift(entry);

    const item = document.createElement('div');
    item.className = 'history-item';
    item.innerHTML = `
        <span class="hi-emotion">${icon}</span>
        <span class="hi-text">${originalText}</span>
        <span class="hi-time">${data.timestamp}</span>
    `;
    item.addEventListener('click', () => {
        renderOutput(entry);
    });
    historyList.prepend(item);
}

// ---- Status ----
function setStatus(state, text) {
    statusDot.className = 'status-dot' + (state === 'busy' ? ' busy' : '');
    statusText.textContent = text;
}
