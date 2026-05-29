<!--
  AnatomyBody.vue — Vis 1 interactive anatomical body (v5.0)
  - Unified with AnatomyHero: same real body outline paths (420×780 viewBox)
  - Anatomically accurate organs: 4-chamber heart, split lung lobes, J-stomach, bean kidneys, coiled intestines
  - viewMode / highlight / hover logic fully preserved
-->
<template>
  <div class="anatomy-wrap" :class="{ 'reduce-motion': reduceMotion }">

    <!-- View Mode Toggle -->
    <div class="mode-toggle" v-if="showToggle">
      <button
        v-for="opt in modeOpts" :key="opt.value"
        class="mode-btn"
        :class="[`mode-${opt.value}`, { 'mode-active': viewMode === opt.value, 'mode-disabled': opt.disabled }]"
        :disabled="opt.disabled"
        :title="opt.disabled ? 'No data available' : ''"
        @click="$emit('update:viewMode', opt.value)"
      >
        <span class="mode-dot" :style="{ background: opt.color }"></span>
        {{ opt.label }}
        <span v-if="opt.count" class="mode-count">{{ opt.count }}</span>
      </button>
    </div>

    <svg viewBox="0 0 420 780" xmlns="http://www.w3.org/2000/svg" class="anatomy-svg">
      <defs>
        <!-- Holographic body fill -->
        <linearGradient id="ab-body-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stop-color="#c9a84c" stop-opacity="0.07"/>
          <stop offset="100%" stop-color="#5c3d0a" stop-opacity="0.03"/>
        </linearGradient>

        <!-- Organ base gradients (resting — slightly coloured so highlights read clearly) -->
        <radialGradient id="ab-brain" cx="0.45" cy="0.4" r="0.65">
          <stop offset="0%"   stop-color="#a78bfa" stop-opacity="0.7"/>
          <stop offset="100%" stop-color="#4c1d95" stop-opacity="0.3"/>
        </radialGradient>
        <radialGradient id="ab-heart" cx="0.38" cy="0.38" r="0.62">
          <stop offset="0%"   stop-color="#f87171" stop-opacity="0.85"/>
          <stop offset="100%" stop-color="#7f1d1d" stop-opacity="0.35"/>
        </radialGradient>
        <radialGradient id="ab-lung" cx="0.5" cy="0.3" r="0.75">
          <stop offset="0%"   stop-color="#c9a84c" stop-opacity="0.6"/>
          <stop offset="100%" stop-color="#5c3d0a" stop-opacity="0.25"/>
        </radialGradient>
        <radialGradient id="ab-liver" cx="0.35" cy="0.35" r="0.8">
          <stop offset="0%"   stop-color="#fbbf24" stop-opacity="0.7"/>
          <stop offset="100%" stop-color="#78350f" stop-opacity="0.3"/>
        </radialGradient>
        <radialGradient id="ab-stomach" cx="0.45" cy="0.35" r="0.75">
          <stop offset="0%"   stop-color="#fb923c" stop-opacity="0.72"/>
          <stop offset="100%" stop-color="#7c2d12" stop-opacity="0.3"/>
        </radialGradient>
        <radialGradient id="ab-kidney" cx="0.4" cy="0.4" r="0.7">
          <stop offset="0%"   stop-color="#c084fc" stop-opacity="0.72"/>
          <stop offset="100%" stop-color="#4c1d95" stop-opacity="0.3"/>
        </radialGradient>
        <radialGradient id="ab-intestine" cx="0.5" cy="0.4" r="0.7">
          <stop offset="0%"   stop-color="#4ade80" stop-opacity="0.5"/>
          <stop offset="100%" stop-color="#14532d" stop-opacity="0.2"/>
        </radialGradient>
        <radialGradient id="ab-muscle" cx="0.5" cy="0.4" r="0.7">
          <stop offset="0%"   stop-color="#fb7185" stop-opacity="0.5"/>
          <stop offset="100%" stop-color="#881337" stop-opacity="0.2"/>
        </radialGradient>

        <!-- Glow filters -->
        <filter id="ab-glow-sm" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="2.5" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        <filter id="ab-glow-md" x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="4.5" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        <filter id="ab-outline-glow" x="-8%" y="-3%" width="116%" height="106%">
          <feGaussianBlur stdDeviation="1.8" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      <!-- ── Layer 1: Body fill ── -->
      <path fill="url(#ab-body-fill)" d="M375.86,438.039c-4.383-1.051-14.305-5.084-17.721-7.705c-3.414-2.625-9.121-5.25-10.98-10.928
        c-8.719-26.635-6.174-42.584-12.33-80.583c-3.279-20.259-10.594-38.978-12.291-49.546c-5.002-31.152,0.314-68.261-9.955-100.304
        c-8.758-27.333-23.908-41.438-41.4-44.698c-20.547-3.037-37.541-14.717-39.795-21.196c0.059-1.203,0.465-5.679,0.793-9.207
        c4.123-3.525,6.537-7.708,7.357-11.811c1.736-8.662,4.16-12.907,4.16-12.907s3.189,1.093,4.959-1.936
        c0.781-1.342,0.545-4.525,1.527-9.028c1.264-5.775,4.736-10.806-0.355-12.834c-2.934-1.165-4.52,0.494-4.52,0.494
        c0.332-1.69,1.822-4.07,2.139-5.757c4.262-22.743-0.867-47.178-22.947-48.343c-8.394-0.442-10.479-0.458-24.623,1.443
        c-23.828,3.204-25.584,26.232-23.307,40.744c0.81,5.156,2.608,9.326,2.658,12.186c0.001,0.001,0.002,0.002,0.004,0.002
        c-1.595-1.072-3.429-1.382-4.965-0.77c-5.09,2.029-1.616,7.059-0.354,12.834c0.984,4.503,0.745,7.687,1.527,9.028
        c1.769,3.029,4.958,1.936,4.958,1.936s2.399,4.245,4.133,12.907c0.822,4.107,3.251,8.295,7.385,11.823
        c0.337,3.668,0.754,8.354,0.795,9.194c-2.256,6.479-19.213,18.159-39.761,21.196c-17.492,3.261-29.013,12.168-36.785,32.724
        c-12.462,32.957-8.649,82.364-14.569,112.278c-2.078,10.5-9.012,29.288-12.291,49.546c-6.157,38-3.612,53.949-12.33,80.583
        c-1.859,5.678-7.566,8.303-10.982,10.928c-3.414,2.617-13.337,6.654-17.719,7.705c-4.387,1.053-12.249,2.311-10.652,5.324
        c1.592,3.008,10.973,3.93,15.565,3.357c4.594-0.572,8.902-2.443,12.412-0.27c3.508,2.172,2.364,6.092,1.015,9.525
        c-1.356,3.438-2.306,5.842-3.521,8.936c-1.221,3.094-4.678,10.863-6.029,14.295c-1.354,3.439-6.797,11.219-1.717,12.424
        c5.086,1.211,7.301-7.443,9.34-10.611c2.04-3.164,6.176-13.77,7.956-13.139c1.779,0.633-0.239,6.652-1.112,9.883
        c-0.876,3.225-3.418,12.158-4.699,16.418c-1.282,4.262-3.459,7.77,0.665,9.393c4.126,1.625,5.53-4.969,5.53-4.969
        s2.207-7.078,3.833-11.203c1.955-4.959,3.715-17.967,5.722-17.484c1.845,0.445,1.681,6.135,1.803,9.328
        c0.125,3.189-0.082,10.957-0.033,15.205c0.046,4.25-0.938,8.068,3.287,8.375c4.221,0.301,3.621-6.111,3.621-6.111
        s0.428-5.977,0.736-10.201c1.229-17.053,1.15-19.08,2.185-19.158c1.035-0.078,2.409,4.799,2.895,7.924
        c0.472,3.031,1.129,10.461,1.644,14.508c0.512,4.051-0.004,7.803,4.057,7.629c4.061-0.178,2.782-6.229,2.782-6.229
        s-0.248-5.75-0.419-9.816c-0.161-3.729-1.881-10.793-2.289-14.807c-0.382-3.178,2.616-10.561,3.377-16.92
        c0.903-10.361-3.785-20.211-3.23-26.406c1.803-20.283,6.973-28.092,14.745-49.844c17.097-47.856,13.28-65.657,15.886-80.78
        c2.605-15.122,10.261-24.323,14.427-40.698c5.112,20.145,7.377,54.859,6.403,76.693c-0.985,22.071-5.784,33.415-8.874,67.759
        c-5.461,29.082,9.767,111.285,9.767,143.623c0,20.951-6.761,36.402-2.704,68.162c12.218,95.697,12.934,104.977,4.644,121.693
        c-3.639,7.344-14.124,12.658-18.891,14.695s-11.323,6.408-17.261,8.039c-5.94,1.631-11.073,5.115-13.702,5.324
        c-2.634,0.213-5.73,0.064-7.277,2.088c-1.55,2.027-1.46,4.814,1.659,7.197c3.114,2.383,8.34,1.688,8.34,1.688
        c-1,0.877,6.705,4.803,11.274,2.691c0,0,2.694,1.32,7.279,2.111c4.58,0.787,15.077-1.311,20.319-3.973
        c5.242-2.654,15.64-6.559,21.285-6.191c5.647,0.365,14.962,3.043,20.338,2.461c5.383-0.574,8.903-3.562,10.314-7.67
        c1.411-4.105-1.256-12.566-3.064-16.664c-1.804-4.1-4.258-14.123-5.387-23.629c-1.456-12.289-2.07-54.711,2.704-72.016
        c5.406-19.596,8.317-48.104,6.963-73.783c-1.35-25.682-1.963-22.494-1.227-34.037c0.442-6.928,6.283-64.115,11.111-101.697
        c4.826,37.582,10.668,94.77,11.109,101.697c0.736,11.543,0.123,8.355-1.227,34.037c-1.354,25.68,1.557,54.188,6.963,73.783
        c4.775,17.305,4.16,59.727,2.705,72.016c-1.129,9.506-3.584,19.529-5.389,23.629c-1.807,4.098-4.475,12.559-3.062,16.664
        c1.41,4.107,4.932,7.096,10.314,7.67c5.375,0.582,14.691-2.096,20.338-2.461c5.646-0.367,16.043,3.537,21.285,6.191
        c5.242,2.662,15.74,4.76,20.32,3.973c4.584-0.791,7.279-2.111,7.279-2.111c4.57,2.111,12.273-1.814,11.273-2.691
        c0,0,5.227,0.695,8.34-1.688c3.119-2.383,3.209-5.17,1.66-7.197c-1.547-2.023-4.645-1.875-7.277-2.088
        c-2.629-0.209-7.762-3.693-13.703-5.324c-5.938-1.631-12.494-6.002-17.26-8.039c-4.768-2.037-15.252-7.352-18.891-14.695
        c-8.291-16.717-7.574-25.996,4.643-121.693c4.057-31.76-2.703-47.211-2.703-68.162c0-32.338,15.229-114.541,9.766-143.623
        c-3.09-34.344-7.889-45.688-8.873-67.759c-0.975-21.834,1.291-56.548,6.402-76.693c4.166,16.375,11.822,25.576,14.428,40.698
        c2.605,15.123-1.211,32.925,15.885,80.781c7.773,21.75,12.943,29.559,14.746,49.842c0.555,6.195-4.135,16.045-3.23,26.406
        c0.76,6.359,3.758,13.744,3.377,16.92c-0.408,4.014-2.129,11.078-2.291,14.809c-0.17,4.064-0.418,9.814-0.418,9.814
        s-1.279,6.051,2.783,6.229c4.059,0.174,3.543-3.578,4.057-7.629c0.514-4.047,1.172-11.477,1.643-14.508
        c0.486-3.125,1.859-8.002,2.895-7.924s0.955,2.105,2.186,19.158c0.309,4.225,0.734,10.201,0.734,10.201s-0.598,6.412,3.623,6.111
        c4.223-0.305,3.24-4.125,3.287-8.375c0.049-4.248-0.158-12.016-0.035-15.205c0.123-3.193-0.041-8.883,1.805-9.328
        c2.006-0.482,3.766,12.525,5.721,17.484c1.627,4.125,3.834,11.203,3.834,11.203s1.402,6.594,5.529,4.969
        c4.123-1.623,1.947-5.131,0.664-9.393c-1.279-4.26-3.822-13.193-4.697-16.418c-0.873-3.23-2.893-9.25-1.113-9.883
        c1.781-0.631,5.916,9.975,7.957,13.139c2.039,3.168,4.254,11.822,9.34,10.611c5.078-1.205-0.363-8.984-1.717-12.424
        c-1.352-3.432-4.809-11.201-6.031-14.295c-1.215-3.094-2.164-5.498-3.52-8.936c-1.35-3.434-2.494-7.354,1.014-9.525
        c3.51-2.174,7.818-0.303,12.412,0.27s10.975-0.35,12.566-3.357C385.108,440.35,380.246,439.092,375.86,438.039z"/>

      <!-- ── Layer 2: Glowing outline (same as hero page) ── -->
      <path class="ab-outline" fill="none" stroke="#c9a84c" stroke-width="1.6"
        filter="url(#ab-outline-glow)"
        d="M375.86,438.039c-4.383-1.051-14.305-5.084-17.721-7.705c-3.414-2.625-9.121-5.25-10.98-10.928
        c-8.719-26.635-6.174-42.584-12.33-80.583c-3.279-20.259-10.594-38.978-12.291-49.546c-5.002-31.152,0.314-68.261-9.955-100.304
        c-8.758-27.333-23.908-41.438-41.4-44.698c-20.547-3.037-37.541-14.717-39.795-21.196c0.059-1.203,0.465-5.679,0.793-9.207
        c4.123-3.525,6.537-7.708,7.357-11.811c1.736-8.662,4.16-12.907,4.16-12.907s3.189,1.093,4.959-1.936
        c0.781-1.342,0.545-4.525,1.527-9.028c1.264-5.775,4.736-10.806-0.355-12.834c-2.934-1.165-4.52,0.494-4.52,0.494
        c0.332-1.69,1.822-4.07,2.139-5.757c4.262-22.743-0.867-47.178-22.947-48.343c-8.394-0.442-10.479-0.458-24.623,1.443
        c-23.828,3.204-25.584,26.232-23.307,40.744c0.81,5.156,2.608,9.326,2.658,12.186c0.001,0.001,0.002,0.002,0.004,0.002
        c-1.595-1.072-3.429-1.382-4.965-0.77c-5.09,2.029-1.616,7.059-0.354,12.834c0.984,4.503,0.745,7.687,1.527,9.028
        c1.769,3.029,4.958,1.936,4.958,1.936s2.399,4.245,4.133,12.907c0.822,4.107,3.251,8.295,7.385,11.823
        c0.337,3.668,0.754,8.354,0.795,9.194c-2.256,6.479-19.213,18.159-39.761,21.196c-17.492,3.261-29.013,12.168-36.785,32.724
        c-12.462,32.957-8.649,82.364-14.569,112.278c-2.078,10.5-9.012,29.288-12.291,49.546c-6.157,38-3.612,53.949-12.33,80.583
        c-1.859,5.678-7.566,8.303-10.982,10.928c-3.414,2.617-13.337,6.654-17.719,7.705c-4.387,1.053-12.249,2.311-10.652,5.324
        c1.592,3.008,10.973,3.93,15.565,3.357c4.594-0.572,8.902-2.443,12.412-0.27c3.508,2.172,2.364,6.092,1.015,9.525
        c-1.356,3.438-2.306,5.842-3.521,8.936c-1.221,3.094-4.678,10.863-6.029,14.295c-1.354,3.439-6.797,11.219-1.717,12.424
        c5.086,1.211,7.301-7.443,9.34-10.611c2.04-3.164,6.176-13.77,7.956-13.139c1.779,0.633-0.239,6.652-1.112,9.883
        c-0.876,3.225-3.418,12.158-4.699,16.418c-1.282,4.262-3.459,7.77,0.665,9.393c4.126,1.625,5.53-4.969,5.53-4.969
        s2.207-7.078,3.833-11.203c1.955-4.959,3.715-17.967,5.722-17.484c1.845,0.445,1.681,6.135,1.803,9.328
        c0.125,3.189-0.082,10.957-0.033,15.205c0.046,4.25-0.938,8.068,3.287,8.375c4.221,0.301,3.621-6.111,3.621-6.111
        s0.428-5.977,0.736-10.201c1.229-17.053,1.15-19.08,2.185-19.158c1.035-0.078,2.409,4.799,2.895,7.924
        c0.472,3.031,1.129,10.461,1.644,14.508c0.512,4.051-0.004,7.803,4.057,7.629c4.061-0.178,2.782-6.229,2.782-6.229
        s-0.248-5.75-0.419-9.816c-0.161-3.729-1.881-10.793-2.289-14.807c-0.382-3.178,2.616-10.561,3.377-16.92
        c0.903-10.361-3.785-20.211-3.23-26.406c1.803-20.283,6.973-28.092,14.745-49.844c17.097-47.856,13.28-65.657,15.886-80.78
        c2.605-15.122,10.261-24.323,14.427-40.698c5.112,20.145,7.377,54.859,6.403,76.693c-0.985,22.071-5.784,33.415-8.874,67.759
        c-5.461,29.082,9.767,111.285,9.767,143.623c0,20.951-6.761,36.402-2.704,68.162c12.218,95.697,12.934,104.977,4.644,121.693
        c-3.639,7.344-14.124,12.658-18.891,14.695s-11.323,6.408-17.261,8.039c-5.94,1.631-11.073,5.115-13.702,5.324
        c-2.634,0.213-5.73,0.064-7.277,2.088c-1.55,2.027-1.46,4.814,1.659,7.197c3.114,2.383,8.34,1.688,8.34,1.688
        c-1,0.877,6.705,4.803,11.274,2.691c0,0,2.694,1.32,7.279,2.111c4.58,0.787,15.077-1.311,20.319-3.973
        c5.242-2.654,15.64-6.559,21.285-6.191c5.647,0.365,14.962,3.043,20.338,2.461c5.383-0.574,8.903-3.562,10.314-7.67
        c1.411-4.105-1.256-12.566-3.064-16.664c-1.804-4.1-4.258-14.123-5.387-23.629c-1.456-12.289-2.07-54.711,2.704-72.016
        c5.406-19.596,8.317-48.104,6.963-73.783c-1.35-25.682-1.963-22.494-1.227-34.037c0.442-6.928,6.283-64.115,11.111-101.697
        c4.826,37.582,10.668,94.77,11.109,101.697c0.736,11.543,0.123,8.355-1.227,34.037c-1.354,25.68,1.557,54.188,6.963,73.783
        c4.775,17.305,4.16,59.727,2.705,72.016c-1.129,9.506-3.584,19.529-5.389,23.629c-1.807,4.098-4.475,12.559-3.062,16.664
        c1.41,4.107,4.932,7.096,10.314,7.67c5.375,0.582,14.691-2.096,20.338-2.461c5.646-0.367,16.043,3.537,21.285,6.191
        c5.242,2.662,15.74,4.76,20.32,3.973c4.584-0.791,7.279-2.111,7.279-2.111c4.57,2.111,12.273-1.814,11.273-2.691
        c0,0,5.227,0.695,8.34-1.688c3.119-2.383,3.209-5.17,1.66-7.197c-1.547-2.023-4.645-1.875-7.277-2.088
        c-2.629-0.209-7.762-3.693-13.703-5.324c-5.938-1.631-12.494-6.002-17.26-8.039c-4.768-2.037-15.252-7.352-18.891-14.695
        c-8.291-16.717-7.574-25.996,4.643-121.693c4.057-31.76-2.703-47.211-2.703-68.162c0-32.338,15.229-114.541,9.766-143.623
        c-3.09-34.344-7.889-45.688-8.873-67.759c-0.975-21.834,1.291-56.548,6.402-76.693c4.166,16.375,11.822,25.576,14.428,40.698
        c2.605,15.123-1.211,32.925,15.885,80.781c7.773,21.75,12.943,29.559,14.746,49.842c0.555,6.195-4.135,16.045-3.23,26.406
        c0.76,6.359,3.758,13.744,3.377,16.92c-0.408,4.014-2.129,11.078-2.291,14.809c-0.17,4.064-0.418,9.814-0.418,9.814
        s-1.279,6.051,2.783,6.229c4.059,0.174,3.543-3.578,4.057-7.629c0.514-4.047,1.172-11.477,1.643-14.508
        c0.486-3.125,1.859-8.002,2.895-7.924s0.955,2.105,2.186,19.158c0.309,4.225,0.734,10.201,0.734,10.201s-0.598,6.412,3.623,6.111
        c4.223-0.305,3.24-4.125,3.287-8.375c0.049-4.248-0.158-12.016-0.035-15.205c0.123-3.193-0.041-8.883,1.805-9.328
        c2.006-0.482,3.766,12.525,5.721,17.484c1.627,4.125,3.834,11.203,3.834,11.203s1.402,6.594,5.529,4.969
        c4.123-1.623,1.947-5.131,0.664-9.393c-1.279-4.26-3.822-13.193-4.697-16.418c-0.873-3.23-2.893-9.25-1.113-9.883
        c1.781-0.631,5.916,9.975,7.957,13.139c2.039,3.168,4.254,11.822,9.34,10.611c5.078-1.205-0.363-8.984-1.717-12.424
        c-1.352-3.432-4.809-11.201-6.031-14.295c-1.215-3.094-2.164-5.498-3.52-8.936c-1.35-3.434-2.494-7.354,1.014-9.525
        c3.51-2.174,7.818-0.303,12.412,0.27s10.975-0.35,12.566-3.357C385.108,440.35,380.246,439.092,375.86,438.039z"/>

      <!-- ── Layer 3: Skeleton ── -->
      <g opacity="0.2">
        <line x1="210" y1="180" x2="210" y2="335" stroke="#bae6fd" stroke-width="1.5"/>
        <path d="M210 206 Q188 198 172 204" stroke="#bae6fd" stroke-width="1.1" fill="none"/>
        <path d="M210 224 Q185 216 168 222" stroke="#bae6fd" stroke-width="1.1" fill="none"/>
        <path d="M210 242 Q184 234 167 240" stroke="#bae6fd" stroke-width="1.1" fill="none"/>
        <path d="M210 260 Q186 252 170 258" stroke="#bae6fd" stroke-width="1.1" fill="none"/>
        <path d="M210 206 Q232 198 248 204" stroke="#bae6fd" stroke-width="1.1" fill="none"/>
        <path d="M210 224 Q235 216 252 222" stroke="#bae6fd" stroke-width="1.1" fill="none"/>
        <path d="M210 242 Q236 234 253 240" stroke="#bae6fd" stroke-width="1.1" fill="none"/>
        <path d="M210 260 Q234 252 250 258" stroke="#bae6fd" stroke-width="1.1" fill="none"/>
        <path d="M178 184 Q195 178 210 181" stroke="#bae6fd" stroke-width="1.3" fill="none"/>
        <path d="M242 184 Q225 178 210 181" stroke="#bae6fd" stroke-width="1.3" fill="none"/>
        <path d="M178 342 Q210 334 242 342 Q252 360 242 370 Q210 378 178 370 Q168 360 178 342Z"
              stroke="#bae6fd" stroke-width="0.9" fill="none"/>
      </g>

      <!-- ── Layer 4: Vasculature ── -->
      <g opacity="0.45">
        <path d="M210 272 Q210 310 210 358 Q208 392 206 428"
              stroke="#ef4444" stroke-width="2" fill="none" class="ab-vessel"/>
        <path d="M214 272 Q214 310 214 358 Q212 392 210 428"
              stroke="#3b82f6" stroke-width="1.5" fill="none" opacity="0.6"/>
        <path d="M198 188 Q194 166 194 116" stroke="#ef4444" stroke-width="1.2" fill="none" opacity="0.6"/>
        <path d="M222 188 Q226 166 226 116" stroke="#ef4444" stroke-width="1.2" fill="none" opacity="0.6"/>
        <path d="M178 194 Q158 240 148 308 Q144 344 148 378" stroke="#ef4444" stroke-width="1" fill="none" opacity="0.4"/>
        <path d="M242 194 Q262 240 272 308 Q276 344 272 378" stroke="#ef4444" stroke-width="1" fill="none" opacity="0.4"/>
      </g>

      <!-- ── Layer 5: Organs (interactive) ── -->
      <g class="organs">

        <!-- BRAIN: dome with gyri folds + hemisphere split -->
        <g v-bind="organHandlers('brain')" class="organ-group" :class="organClass('brain')">
          <!-- Main brain dome -->
          <path d="M174 75 Q174 43 210 39 Q246 43 246 75 Q246 107 210 111 Q174 107 174 75Z"
                fill="url(#ab-brain)"/>
          <!-- Gyri (sulcal folds) -->
          <path d="M179 63 Q192 57 206 63 Q218 57 230 63" stroke="#c4b5fd" stroke-width="1" fill="none" opacity="0.55"/>
          <path d="M177 76 Q192 70 208 76 Q222 70 236 76" stroke="#c4b5fd" stroke-width="1" fill="none" opacity="0.55"/>
          <path d="M179 89 Q192 83 208 89 Q220 83 234 89" stroke="#c4b5fd" stroke-width="0.9" fill="none" opacity="0.45"/>
          <!-- Hemisphere split -->
          <line x1="210" y1="40" x2="210" y2="110" stroke="#ddd6fe" stroke-width="0.8" opacity="0.4"/>
          <!-- Cerebellum hint -->
          <path d="M186 103 Q198 109 210 111 Q222 109 234 103"
                stroke="#a78bfa" stroke-width="1.2" fill="none" opacity="0.4"/>
        </g>

        <!-- EYES: realistic with iris + pupil -->
        <g v-bind="organHandlers('eye')" class="organ-group" :class="organClass('eye')">
          <ellipse cx="190" cy="67" rx="7" ry="4.5" fill="#dbeafe" opacity="0.9"/>
          <ellipse cx="190" cy="67" rx="3.5" ry="3.5" fill="#1e40af" opacity="0.8"/>
          <circle  cx="191.5" cy="66" r="1.2" fill="#e0f2fe" opacity="0.9"/>
          <ellipse cx="230" cy="67" rx="7" ry="4.5" fill="#dbeafe" opacity="0.9"/>
          <ellipse cx="230" cy="67" rx="3.5" ry="3.5" fill="#1e40af" opacity="0.8"/>
          <circle  cx="231.5" cy="66" r="1.2" fill="#e0f2fe" opacity="0.9"/>
        </g>

        <!-- EAR: at sides of head (~x=174-180 left, x=240-246 right) -->
        <g v-bind="organHandlers('ear')" class="organ-group" :class="organClass('ear')">
          <!-- Left ear -->
          <path d="M175 65 Q169 69 169 76 Q169 83 175 86 Q178 86 179 81 Q177 75 178 70 Q178 66 175 65Z"
                fill="none" :stroke="organStroke('ear')" stroke-width="2" stroke-linecap="round"/>
          <!-- Right ear -->
          <path d="M245 65 Q251 69 251 76 Q251 83 245 86 Q242 86 241 81 Q243 75 242 70 Q242 66 245 65Z"
                fill="none" :stroke="organStroke('ear')" stroke-width="2" stroke-linecap="round"/>
        </g>

        <!-- HEART: anatomically shaped with 4-chamber hint + aortic arch -->
        <g v-bind="organHandlers('heart')" class="organ-group ab-heart-beat" :class="organClass('heart')">
          <!-- Heart body: 2 atria on top, apex pointing left-down -->
          <path d="M212 233
                   C 203 221, 187 227, 190 245
                   C 193 260, 207 271, 220 281
                   C 227 274, 243 263, 247 247
                   C 251 231, 237 223, 228 233
                   C 225 228, 217 228, 212 233Z"
                fill="url(#ab-heart)"/>
          <!-- Inter-ventricular groove hint -->
          <path d="M221 247 Q222 263 220 279" stroke="#fda4af" stroke-width="0.8" fill="none" opacity="0.5"/>
          <!-- Aortic arch -->
          <path d="M228 233 Q235 219 239 211 Q245 205 253 207"
                stroke="#ef4444" stroke-width="1.5" fill="none" opacity="0.6"/>
          <!-- Pulmonary trunk -->
          <path d="M219 233 Q215 220 213 213 Q210 205 201 203"
                stroke="#4a90c4" stroke-width="1.2" fill="none" opacity="0.55"/>
        </g>

        <!-- LUNGS: fit within chest cavity x=168-252 -->
        <g v-bind="organHandlers('lung')" class="organ-group ab-lung-breath" :class="organClass('lung')">
          <!-- Left lung (2 lobes, narrower due to heart, x=168-200) -->
          <path d="M183 205 Q171 212 169 244 Q168 270 171 290 Q176 310 187 314 Q199 312 201 298 L201 220 Q195 200 183 205Z"
                fill="url(#ab-lung)"/>
          <!-- Left oblique fissure -->
          <path d="M201 228 Q187 256 175 292" stroke="#bae6fd" stroke-width="1" fill="none" opacity="0.45"/>
          <!-- Left bronchus -->
          <path d="M201 236 Q190 248 180 264" stroke="#e8c97a" stroke-width="1" fill="none" opacity="0.5"/>

          <!-- Right lung (3 lobes, x=220-252) -->
          <path d="M237 202 Q249 210 251 244 Q252 272 249 292 Q243 312 232 314 Q221 312 219 298 L219 215 Q225 198 237 202Z"
                fill="url(#ab-lung)"/>
          <!-- Right horizontal fissure -->
          <path d="M219 238 Q235 240 247 238" stroke="#bae6fd" stroke-width="1" fill="none" opacity="0.45"/>
          <!-- Right oblique fissure -->
          <path d="M219 236 Q233 260 245 294" stroke="#bae6fd" stroke-width="1" fill="none" opacity="0.4"/>
          <!-- Right bronchus -->
          <path d="M219 234 Q231 244 243 260" stroke="#e8c97a" stroke-width="1" fill="none" opacity="0.5"/>
        </g>

        <!-- LIVER: right-biased wedge within torso boundary (x=178-252) -->
        <g v-bind="organHandlers('liver')" class="organ-group" :class="organClass('liver')">
          <path d="M180 300 Q175 296 178 290 Q206 286 244 290 Q252 294 252 308 Q250 328 240 334 Q224 339 210 337 Q194 334 184 324 Q178 316 180 300Z"
                fill="url(#ab-liver)"/>
          <!-- Lobule texture -->
          <path d="M192 308 Q220 303 246 308" stroke="#fde68a" stroke-width="0.7" fill="none" opacity="0.35"/>
          <path d="M190 320 Q218 315 244 320" stroke="#fde68a" stroke-width="0.7" fill="none" opacity="0.3"/>
          <!-- Gallbladder -->
          <ellipse cx="232" cy="342" rx="8" ry="6" fill="#fbbf24" opacity="0.45"/>
        </g>

        <!-- STOMACH: J-shape within torso (x=166-214) -->
        <g v-bind="organHandlers('stomach')" class="organ-group" :class="organClass('stomach')">
          <path d="M177 300 Q169 303 167 316 Q166 330 169 344 Q173 358 184 361 Q195 362 205 354 Q214 346 213 333 Q211 321 206 316 Q198 300 186 298 Q181 297 177 300Z"
                fill="url(#ab-stomach)"/>
          <path d="M173 318 Q185 314 200 320" stroke="#fdba74" stroke-width="0.8" fill="none" opacity="0.4"/>
          <path d="M171 330 Q184 326 200 332" stroke="#fdba74" stroke-width="0.8" fill="none" opacity="0.35"/>
          <path d="M210 333 Q215 333 218 337" stroke="#fb923c" stroke-width="1.2" fill="none" opacity="0.6"/>
        </g>

        <!-- KIDNEYS: bean shapes within lower abdomen (left x=172-200, right x=220-248) -->
        <g v-bind="organHandlers('kidney')" class="organ-group" :class="organClass('kidney')">
          <!-- Left kidney: hilum notch faces right (toward spine) -->
          <path d="M182 292 Q172 294 170 305 Q170 318 180 325 Q190 329 198 321 Q202 315 200 305 Q198 295 190 291 Q186 290 182 292Z"
                fill="url(#ab-kidney)"/>
          <path d="M198 306 Q200 306 198 312" stroke="#c4b5fd" stroke-width="1.2" fill="none" opacity="0.55"/>

          <!-- Right kidney: hilum notch faces left (toward spine) -->
          <path d="M238 292 Q248 294 250 305 Q250 318 240 325 Q230 329 222 321 Q218 315 220 305 Q222 295 230 291 Q234 290 238 292Z"
                fill="url(#ab-kidney)"/>
          <path d="M222 306 Q220 306 222 312" stroke="#c4b5fd" stroke-width="1.2" fill="none" opacity="0.55"/>
        </g>

        <!-- SKIN: holographic outline ring (whole body outline as "skin" layer) -->
        <g v-bind="organHandlers('skin')" class="organ-group" :class="organClass('skin')">
          <path fill="none" :stroke="organStroke('skin')" stroke-width="3" opacity="0.45"
            d="M375.86,438.039c-4.383-1.051-14.305-5.084-17.721-7.705c-3.414-2.625-9.121-5.25-10.98-10.928
            c-8.719-26.635-6.174-42.584-12.33-80.583c-3.279-20.259-10.594-38.978-12.291-49.546c-5.002-31.152,0.314-68.261-9.955-100.304
            c-8.758-27.333-23.908-41.438-41.4-44.698c-20.547-3.037-37.541-14.717-39.795-21.196c0.059-1.203,0.465-5.679,0.793-9.207
            c4.123-3.525,6.537-7.708,7.357-11.811c1.736-8.662,4.16-12.907,4.16-12.907s3.189,1.093,4.959-1.936
            c0.781-1.342,0.545-4.525,1.527-9.028c1.264-5.775,4.736-10.806-0.355-12.834c-2.934-1.165-4.52,0.494-4.52,0.494
            c0.332-1.69,1.822-4.07,2.139-5.757c4.262-22.743-0.867-47.178-22.947-48.343c-8.394-0.442-10.479-0.458-24.623,1.443
            c-23.828,3.204-25.584,26.232-23.307,40.744c0.81,5.156,2.608,9.326,2.658,12.186c0.001,0.001,0.002,0.002,0.004,0.002
            c-1.595-1.072-3.429-1.382-4.965-0.77c-5.09,2.029-1.616,7.059-0.354,12.834c0.984,4.503,0.745,7.687,1.527,9.028
            c1.769,3.029,4.958,1.936,4.958,1.936s2.399,4.245,4.133,12.907c0.822,4.107,3.251,8.295,7.385,11.823
            c0.337,3.668,0.754,8.354,0.795,9.194c-2.256,6.479-19.213,18.159-39.761,21.196c-17.492,3.261-29.013,12.168-36.785,32.724
            c-12.462,32.957-8.649,82.364-14.569,112.278c-2.078,10.5-9.012,29.288-12.291,49.546c-6.157,38-3.612,53.949-12.33,80.583
            c-1.859,5.678-7.566,8.303-10.982,10.928c-3.414,2.617-13.337,6.654-17.719,7.705c-4.387,1.053-12.249,2.311-10.652,5.324
            c1.592,3.008,10.973,3.93,15.565,3.357c4.594-0.572,8.902-2.443,12.412-0.27c3.508,2.172,2.364,6.092,1.015,9.525
            c-1.356,3.438-2.306,5.842-3.521,8.936c-1.221,3.094-4.678,10.863-6.029,14.295c-1.354,3.439-6.797,11.219-1.717,12.424
            c5.086,1.211,7.301-7.443,9.34-10.611c2.04-3.164,6.176-13.77,7.956-13.139c1.779,0.633-0.239,6.652-1.112,9.883
            c-0.876,3.225-3.418,12.158-4.699,16.418c-1.282,4.262-3.459,7.77,0.665,9.393c4.126,1.625,5.53-4.969,5.53-4.969
            s2.207-7.078,3.833-11.203c1.955-4.959,3.715-17.967,5.722-17.484c1.845,0.445,1.681,6.135,1.803,9.328
            c0.125,3.189-0.082,10.957-0.033,15.205c0.046,4.25-0.938,8.068,3.287,8.375c4.221,0.301,3.621-6.111,3.621-6.111
            s0.428-5.977,0.736-10.201c1.229-17.053,1.15-19.08,2.185-19.158c1.035-0.078,2.409,4.799,2.895,7.924
            c0.472,3.031,1.129,10.461,1.644,14.508c0.512,4.051-0.004,7.803,4.057,7.629c4.061-0.178,2.782-6.229,2.782-6.229
            s-0.248-5.75-0.419-9.816c-0.161-3.729-1.881-10.793-2.289-14.807c-0.382-3.178,2.616-10.561,3.377-16.92
            c0.903-10.361-3.785-20.211-3.23-26.406c1.803-20.283,6.973-28.092,14.745-49.844c17.097-47.856,13.28-65.657,15.886-80.78
            c2.605-15.122,10.261-24.323,14.427-40.698c5.112,20.145,7.377,54.859,6.403,76.693c-0.985,22.071-5.784,33.415-8.874,67.759
            c-5.461,29.082,9.767,111.285,9.767,143.623c0,20.951-6.761,36.402-2.704,68.162c12.218,95.697,12.934,104.977,4.644,121.693
            c-3.639,7.344-14.124,12.658-18.891,14.695s-11.323,6.408-17.261,8.039c-5.94,1.631-11.073,5.115-13.702,5.324
            c-2.634,0.213-5.73,0.064-7.277,2.088c-1.55,2.027-1.46,4.814,1.659,7.197c3.114,2.383,8.34,1.688,8.34,1.688
            c-1,0.877,6.705,4.803,11.274,2.691c0,0,2.694,1.32,7.279,2.111c4.58,0.787,15.077-1.311,20.319-3.973
            c5.242-2.654,15.64-6.559,21.285-6.191c5.647,0.365,14.962,3.043,20.338,2.461c5.383-0.574,8.903-3.562,10.314-7.67
            c1.411-4.105-1.256-12.566-3.064-16.664c-1.804-4.1-4.258-14.123-5.387-23.629c-1.456-12.289-2.07-54.711,2.704-72.016
            c5.406-19.596,8.317-48.104,6.963-73.783c-1.35-25.682-1.963-22.494-1.227-34.037c0.442-6.928,6.283-64.115,11.111-101.697
            c4.826,37.582,10.668,94.77,11.109,101.697c0.736,11.543,0.123,8.355-1.227,34.037c-1.354,25.68,1.557,54.188,6.963,73.783
            c4.775,17.305,4.16,59.727,2.705,72.016c-1.129,9.506-3.584,19.529-5.389,23.629c-1.807,4.098-4.475,12.559-3.062,16.664
            c1.41,4.107,4.932,7.096,10.314,7.67c5.375,0.582,14.691-2.096,20.338-2.461c5.646-0.367,16.043,3.537,21.285,6.191
            c5.242,2.662,15.74,4.76,20.32,3.973c4.584-0.791,7.279-2.111,7.279-2.111c4.57,2.111,12.273-1.814,11.273-2.691
            c0,0,5.227,0.695,8.34-1.688c3.119-2.383,3.209-5.17,1.66-7.197c-1.547-2.023-4.645-1.875-7.277-2.088
            c-2.629-0.209-7.762-3.693-13.703-5.324c-5.938-1.631-12.494-6.002-17.26-8.039c-4.768-2.037-15.252-7.352-18.891-14.695
            c-8.291-16.717-7.574-25.996,4.643-121.693c4.057-31.76-2.703-47.211-2.703-68.162c0-32.338,15.229-114.541,9.766-143.623
            c-3.09-34.344-7.889-45.688-8.873-67.759c-0.975-21.834,1.291-56.548,6.402-76.693c4.166,16.375,11.822,25.576,14.428,40.698
            c2.605,15.123-1.211,32.925,15.885,80.781c7.773,21.75,12.943,29.559,14.746,49.842c0.555,6.195-4.135,16.045-3.23,26.406
            c0.76,6.359,3.758,13.744,3.377,16.92c-0.408,4.014-2.129,11.078-2.291,14.809c-0.17,4.064-0.418,9.814-0.418,9.814
            s-1.279,6.051,2.783,6.229c4.059,0.174,3.543-3.578,4.057-7.629c0.514-4.047,1.172-11.477,1.643-14.508
            c0.486-3.125,1.859-8.002,2.895-7.924s0.955,2.105,2.186,19.158c0.309,4.225,0.734,10.201,0.734,10.201s-0.598,6.412,3.623,6.111
            c4.223-0.305,3.24-4.125,3.287-8.375c0.049-4.248-0.158-12.016-0.035-15.205c0.123-3.193-0.041-8.883,1.805-9.328
            c2.006-0.482,3.766,12.525,5.721,17.484c1.627,4.125,3.834,11.203,3.834,11.203s1.402,6.594,5.529,4.969
            c4.123-1.623,1.947-5.131,0.664-9.393c-1.279-4.26-3.822-13.193-4.697-16.418c-0.873-3.23-2.893-9.25-1.113-9.883
            c1.781-0.631,5.916,9.975,7.957,13.139c2.039,3.168,4.254,11.822,9.34,10.611c5.078-1.205-0.363-8.984-1.717-12.424
            c-1.352-3.432-4.809-11.201-6.031-14.295c-1.215-3.094-2.164-5.498-3.52-8.936c-1.35-3.434-2.494-7.354,1.014-9.525
            c3.51-2.174,7.818-0.303,12.412,0.27s10.975-0.35,12.566-3.357C385.108,440.35,380.246,439.092,375.86,438.039z"/>
        </g>

        <!-- MUSCLE: quadriceps groups on both thighs -->
        <g v-bind="organHandlers('muscle')" class="organ-group" :class="organClass('muscle')">
          <!-- Left thigh front -->
          <path d="M187 500 Q181 508 180 530 Q181 552 187 562 Q193 565 197 560
                   Q200 544 200 522 Q199 508 194 500Z"
                fill="url(#ab-muscle)"/>
          <!-- Right thigh front -->
          <path d="M233 500 Q239 508 240 530 Q239 552 233 562 Q227 565 223 560
                   Q220 544 220 522 Q221 508 226 500Z"
                fill="url(#ab-muscle)"/>
        </g>

        <!-- BLOOD / vascular highlight: brachial vessels (arms) -->
        <g v-bind="organHandlers('blood')" class="organ-group" :class="organClass('blood')">
          <ellipse cx="88" cy="310" rx="7" ry="28" fill="url(#ab-heart)" opacity="0.55"/>
          <ellipse cx="332" cy="310" rx="7" ry="28" fill="url(#ab-heart)" opacity="0.55"/>
        </g>

        <!-- VASCULAR: aortic arch visible above heart -->
        <g v-bind="organHandlers('vascular')" class="organ-group" :class="organClass('vascular')">
          <path d="M210 200 Q218 190 228 194 Q238 198 238 210"
                fill="none" :stroke="organStroke('vascular')" stroke-width="3.5" stroke-linecap="round"
                opacity="0.8"/>
          <path d="M210 200 Q202 190 192 194"
                fill="none" :stroke="organStroke('vascular')" stroke-width="2.5" stroke-linecap="round"
                opacity="0.65"/>
        </g>

        <!-- ENDOCRINE: pituitary + thyroid + adrenals (updated to match new kidney tops) + pancreas -->
        <g v-bind="organHandlers('endocrine')" class="organ-group" :class="organClass('endocrine')">
          <!-- Pituitary (just below brain base) -->
          <circle cx="210" cy="113" r="4" fill="url(#ab-brain)" opacity="0.8"/>
          <!-- Thyroid (butterfly, neck x=200-220) -->
          <path d="M200 160 Q205 155 210 158 Q215 155 220 160 Q218 170 210 172 Q202 170 200 160Z"
                fill="url(#ab-brain)" opacity="0.7"/>
          <!-- Adrenal caps on kidney tops (left ~x=188-196, right ~x=224-232) -->
          <path d="M188 290 Q192 283 196 290Z" fill="url(#ab-brain)" opacity="0.7"/>
          <path d="M232 290 Q228 283 224 290Z" fill="url(#ab-brain)" opacity="0.7"/>
          <!-- Pancreas -->
          <path d="M198 316 Q218 312 236 316 Q240 322 236 326 Q218 322 198 326 Q194 322 198 316Z"
                fill="url(#ab-brain)" opacity="0.55"/>
        </g>

        <!-- REPRODUCTIVE: uterus + bladder -->
        <g v-bind="organHandlers('reproductive')" class="organ-group" :class="organClass('reproductive')">
          <!-- Bladder (dome-shaped) -->
          <path d="M198 442 Q189 444 187 452 Q187 462 198 466
                   Q210 468 222 466 Q233 462 233 452 Q231 444 222 442
                   Q212 439 198 442Z"
                fill="url(#ab-stomach)" opacity="0.6"/>
          <!-- Uterus (pear, slightly above bladder) -->
          <path d="M205 428 Q200 428 198 433 Q198 440 205 442
                   Q210 443 215 442 Q222 440 222 433 Q220 428 215 428
                   Q210 426 205 428Z"
                fill="url(#ab-stomach)" opacity="0.5"/>
        </g>

        <!-- IMMUNE: spleen (within body boundary) + cervical + axillary + inguinal nodes -->
        <g v-bind="organHandlers('immune')" class="organ-group" :class="organClass('immune')">
          <!-- Spleen (upper-left abdomen, x=168-188, within body boundary) -->
          <path d="M175 284 Q168 288 168 300 Q168 310 175 314 Q184 314 188 306 Q188 294 183 288 Q180 282 175 284Z"
                fill="#a78bfa" opacity="0.65"/>
          <!-- Cervical nodes (neck, x=196-224) -->
          <circle cx="196" cy="160" r="4" fill="#a78bfa" opacity="0.6"/>
          <circle cx="224" cy="160" r="4" fill="#a78bfa" opacity="0.6"/>
          <!-- Axillary nodes (armpit, moved closer to body) -->
          <circle cx="152" cy="210" r="4" fill="#a78bfa" opacity="0.55"/>
          <circle cx="268" cy="210" r="4" fill="#a78bfa" opacity="0.55"/>
          <!-- Inguinal nodes (groin) -->
          <circle cx="185" cy="444" r="4" fill="#a78bfa" opacity="0.55"/>
          <circle cx="235" cy="444" r="4" fill="#a78bfa" opacity="0.55"/>
        </g>

      </g>

    </svg>

  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Effect } from '../api/client'

export type ViewMode = 'benefits' | 'side_effects' | 'both' | 'neutral'

const props = defineProps<{
  effects: Effect[]
  hovered: string | null
  viewMode: ViewMode
  reduceMotion?: boolean
  showToggle?: boolean
  benefitCount?: number
  sideCount?: number
}>()

const emit = defineEmits<{
  'update:hovered':  [value: string | null]
  'update:viewMode': [value: ViewMode]
}>()

const modeOpts = computed(() => [
  { value: 'neutral'      as ViewMode, label: 'Overview',     color: '#60a5fa', count: undefined,          disabled: false },
  { value: 'benefits'     as ViewMode, label: 'Benefits',     color: '#4ade80', count: props.benefitCount, disabled: (props.benefitCount ?? 0) === 0 },
  { value: 'both'         as ViewMode, label: 'Both',         color: '#facc15', count: undefined,          disabled: false },
  { value: 'side_effects' as ViewMode, label: 'Side Effects', color: '#ff2020', count: props.sideCount,    disabled: (props.sideCount ?? 0) === 0 },
])

const effectMap = computed(() => {
  const map = new Map<string, Effect[]>()
  for (const e of props.effects) {
    if (!matchesMode(e)) continue
    if (!map.has(e.body_part)) map.set(e.body_part, [])
    map.get(e.body_part)!.push(e)
  }
  return map
})

function matchesMode(e: Effect): boolean {
  if (props.viewMode === 'both' || props.viewMode === 'neutral') return true
  if (props.viewMode === 'benefits') return e.effect_type === 'benefit'
  return e.effect_type === 'side_effect'
}
function effectsAt(p: string): Effect[] { return effectMap.value.get(p) ?? [] }
function maxSeverity(p: string): number {
  return effectsAt(p).reduce((acc, e) => Math.max(acc, ({high:3,medium:2,low:1,unknown:0}[e.severity as string] ?? 0)), 0)
}
function highlightType(p: string): 'none'|'benefit'|'side'|'both'|'neutral' {
  const fx = effectsAt(p); if (!fx.length) return 'none'
  if (props.viewMode === 'neutral') return 'neutral'
  const hasB = fx.some(e => e.effect_type === 'benefit')
  const hasSE = fx.some(e => e.effect_type === 'side_effect')
  return hasB && hasSE ? 'both' : hasB ? 'benefit' : 'side'
}
function organClass(p: string) {
  const hl = highlightType(p)
  return [`hl-${hl}`, props.hovered === p ? 'hovered' : '', props.hovered && props.hovered !== p ? 'dim' : '',
          maxSeverity(p) >= 3 && !props.reduceMotion ? 'pulse-strong' : '', hl === 'none' ? 'inactive' : '']
}
function organFilter(_p: string): string { return '' }
function organStroke(p: string): string {
  const hl = highlightType(p)
  return hl==='benefit'?'#4ade80': hl==='side'?'#ff2020': hl==='both'?'#facc15': hl==='neutral'?'#60a5fa':'#c9a84c'
}
function organHandlers(p: string) {
  return {
    onMouseenter: () => emit('update:hovered', p),
    onMouseleave: () => emit('update:hovered', null),
    onFocus:      () => emit('update:hovered', p),
    onBlur:       () => emit('update:hovered', null),
    tabindex: highlightType(p) === 'none' ? -1 : 0,
    role: 'button', 'aria-label': `${p} region`,
  }
}

const hoveredColor = computed(() => {
  if (!props.hovered) return '#94a3b8'
  const hl = highlightType(props.hovered)
  return hl === 'benefit' ? '#4ade80' : hl === 'side' ? '#ff2020' : hl === 'both' ? '#facc15' : hl === 'neutral' ? '#60a5fa' : '#c9a84c'
})

const bpLabels: Record<string, string> = {
  brain: 'Brain', eye: 'Eyes', ear: 'Ears', heart: 'Heart',
  lung: 'Lungs', liver: 'Liver', stomach: 'Stomach', kidney: 'Kidneys',
  skin: 'Skin', muscle: 'Muscles', blood: 'Blood System',
  vascular: 'Vascular System', endocrine: 'Endocrine System',
  reproductive: 'Reproductive System', immune: 'Immune System',
}
function bodyPartLabel(p: string): string {
  return bpLabels[p] ?? (p.charAt(0).toUpperCase() + p.slice(1))
}
</script>

<style scoped>
.anatomy-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  user-select: none;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

/* ── Toggle ── */
.mode-toggle { display: flex; gap: 6px; padding: 4px; background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; }
.mode-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 14px; background: transparent; border: none;
  color: #94a3b8; font-size: .82rem; font-weight: 500; border-radius: 8px;
  cursor: pointer; transition: background .15s, color .15s;
}
.mode-btn:hover:not(:disabled) { background: #1e293b; color: #e2e8f0; }
.mode-active { background: #1e293b; color: #f1f5f9; }
.mode-active.mode-neutral      { box-shadow: inset 0 0 0 1px #1d4ed8; color: #60a5fa; }
.mode-active.mode-benefits     { box-shadow: inset 0 0 0 1px #16a34a; color: #4ade80; }
.mode-active.mode-side_effects { box-shadow: inset 0 0 0 1px #cc0000; color: #ff2020; }
.mode-active.mode-both         { box-shadow: inset 0 0 0 1px #b45309; color: #facc15; }
.mode-disabled { opacity: 0.35; cursor: not-allowed; }
.mode-dot { width: 8px; height: 8px; border-radius: 50%; }
.mode-count { background: rgba(255,255,255,.06); padding: 1px 6px; border-radius: 8px; font-size: .68rem; }

/* ── SVG ── */
.anatomy-svg {
  width: auto;
  max-width: 100%;
  height: 100%;
  max-height: 100%;
  display: block;
  filter: drop-shadow(0 0 30px rgba(201,168,76,0.18));
}

/* Outline breathe */
.ab-outline { animation: ab-outline-breathe 4s ease-in-out infinite; }
@keyframes ab-outline-breathe {
  0%,100% { opacity: 0.65; }
  50%     { opacity: 0.9; }
}

/* Heart beat — origin at heart center (220, 257) in 420×780 space */
.ab-heart-beat {
  transform-origin: 220px 257px;
  animation: ab-heart 1.15s ease-in-out infinite;
}
@keyframes ab-heart {
  0%,100% { transform: scale(1); }
  20%     { transform: scale(1.05); }
  40%     { transform: scale(0.99); }
  60%     { transform: scale(1.03); }
  80%     { transform: scale(1.00); }
}

/* Lung breath — origin at lung midpoint */
.ab-lung-breath {
  transform-origin: 210px 258px;
  animation: ab-lung 4.2s ease-in-out infinite;
}
@keyframes ab-lung {
  0%,100% { transform: scale(1); }
  50%     { transform: scale(1.05); }
}

/* Blood vessel pulse */
.ab-vessel {
  stroke-dasharray: 4 8;
  animation: ab-flow 16s linear infinite;
}
@keyframes ab-flow {
  0%   { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: -240; }
}

.reduce-motion .ab-outline,
.reduce-motion .ab-heart-beat,
.reduce-motion .ab-lung-breath,
.reduce-motion .ab-vessel,
.reduce-motion .pulse-strong { animation: none !important; }

/* ── Organ states ── */
.organ-group {
  cursor: pointer; outline: none;
  filter: saturate(0.14) brightness(0.52);
  transition: filter .3s ease, opacity .25s ease, transform .15s ease;
}
.organ-group.inactive { cursor: default; filter: saturate(0.06) brightness(0.38); opacity: 0.6; }
/* No scale on hover — prevents layout jump; glow from hl- rules is sufficient feedback */
.organ-group.dim { filter: saturate(0.04) brightness(0.26) !important; opacity: 0.35; }

/* Highlights */
.organ-group.hl-benefit {
  filter: grayscale(1) sepia(1) hue-rotate(90deg) saturate(4) brightness(1.35)
          drop-shadow(0 0 8px rgba(34,197,94,.65));
}
.organ-group.hl-benefit.hovered,
.organ-group.hl-benefit:not(.inactive):hover {
  filter: grayscale(1) sepia(1) hue-rotate(90deg) saturate(5) brightness(1.6)
          drop-shadow(0 0 18px rgba(34,197,94,.95)) drop-shadow(0 0 5px rgba(34,197,94,.5));
}
.organ-group.hl-side {
  filter: grayscale(1) sepia(1) hue-rotate(330deg) saturate(8) brightness(1.1)
          drop-shadow(0 0 10px rgba(255,32,32,.75));
}
.organ-group.hl-side.hovered,
.organ-group.hl-side:not(.inactive):hover {
  filter: grayscale(1) sepia(1) hue-rotate(330deg) saturate(10) brightness(1.35)
          drop-shadow(0 0 20px rgba(255,32,32,1)) drop-shadow(0 0 6px rgba(255,32,32,.6));
}
.organ-group.hl-both {
  filter: grayscale(1) sepia(1) hue-rotate(28deg) saturate(4) brightness(1.25)
          drop-shadow(0 0 8px rgba(245,158,11,.65));
}
.organ-group.hl-both.hovered,
.organ-group.hl-both:not(.inactive):hover {
  filter: grayscale(1) sepia(1) hue-rotate(28deg) saturate(5) brightness(1.45)
          drop-shadow(0 0 18px rgba(245,158,11,.95));
}
.organ-group.hl-neutral {
  filter: grayscale(1) sepia(1) hue-rotate(165deg) saturate(3) brightness(1.25)
          drop-shadow(0 0 8px rgba(96,165,250,.65));
}
.organ-group.hl-neutral.hovered,
.organ-group.hl-neutral:not(.inactive):hover {
  filter: grayscale(1) sepia(1) hue-rotate(165deg) saturate(4) brightness(1.5)
          drop-shadow(0 0 18px rgba(96,165,250,.95)) drop-shadow(0 0 5px rgba(96,165,250,.5));
}

@keyframes pulse-green {
  0%,100% { filter: grayscale(1) sepia(1) hue-rotate(90deg) saturate(4) brightness(1.35) drop-shadow(0 0 8px rgba(34,197,94,.65)); }
  50%     { filter: grayscale(1) sepia(1) hue-rotate(90deg) saturate(5) brightness(1.7) drop-shadow(0 0 22px rgba(34,197,94,1)); }
}
@keyframes pulse-red {
  0%,100% { filter: grayscale(1) sepia(1) hue-rotate(330deg) saturate(8) brightness(1.1) drop-shadow(0 0 10px rgba(255,32,32,.75)); }
  50%     { filter: grayscale(1) sepia(1) hue-rotate(330deg) saturate(12) brightness(1.5) drop-shadow(0 0 24px rgba(255,32,32,1)); }
}
@keyframes pulse-amber {
  0%,100% { filter: grayscale(1) sepia(1) hue-rotate(28deg) saturate(4) brightness(1.25) drop-shadow(0 0 8px rgba(245,158,11,.65)); }
  50%     { filter: grayscale(1) sepia(1) hue-rotate(28deg) saturate(6) brightness(1.55) drop-shadow(0 0 22px rgba(245,158,11,1)); }
}
@keyframes pulse-neutral {
  0%,100% { filter: grayscale(1) sepia(1) hue-rotate(165deg) saturate(3) brightness(1.25) drop-shadow(0 0 8px rgba(96,165,250,.65)); }
  50%     { filter: grayscale(1) sepia(1) hue-rotate(165deg) saturate(5) brightness(1.6) drop-shadow(0 0 22px rgba(96,165,250,1)); }
}
.pulse-strong.hl-benefit { animation: pulse-green   1.8s ease-in-out infinite; }
.pulse-strong.hl-side    { animation: pulse-red     1.8s ease-in-out infinite; }
.pulse-strong.hl-both    { animation: pulse-amber   1.8s ease-in-out infinite; }
.pulse-strong.hl-neutral { animation: pulse-neutral 1.8s ease-in-out infinite; }

/* Organ hover panel */
.hover-panel {
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: .85rem;
}
.hp-dot {
  width: 9px; height: 9px; border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 8px currentColor;
}
.hp-name { color: #e2e8f0; font-weight: 600; letter-spacing: 0.04em; }
.hp-effects { color: #64748b; font-size: .78rem; }
.hp-hint { color: #334155; font-style: italic; font-size: .78rem; }

/* Legend */
.legend { display: flex; gap: 16px; font-size: .76rem; color: #64748b; align-items: center; flex-wrap: wrap; }
.leg { display: flex; align-items: center; gap: 5px; }
.leg-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; }
.leg-dot.benefit { background: #4ade80; box-shadow: 0 0 6px #4ade80; }
.leg-dot.side    { background: #f87171; box-shadow: 0 0 6px #f87171; }
.leg-dot.both    { background: #facc15; box-shadow: 0 0 6px #facc15; }
.leg-meta { color: #475569; }
</style>
