<!--
  AnatomyHero.vue — 首页装饰用解剖人体（v3.5 新）

  - 非交互，纯视觉
  - 心跳 / 呼吸 / 血流粒子动画
  - 与 AnatomyBody.vue 同一风格语言，仅作背景层
  - prefers-reduced-motion 支持
-->
<template>
  <div class="hero-anatomy" :class="{ 'reduce-motion': reduceMotion }">
    <svg viewBox="0 0 260 540" xmlns="http://www.w3.org/2000/svg" class="hero-svg">
      <defs>
        <radialGradient id="hero-head" cx="0.5" cy="0.4" r="0.7">
          <stop offset="0%" stop-color="#26334a"/>
          <stop offset="100%" stop-color="#0f172a"/>
        </radialGradient>
        <linearGradient id="hero-skin" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"  stop-color="#1e293b" stop-opacity="0.75"/>
          <stop offset="50%" stop-color="#172033" stop-opacity="0.85"/>
          <stop offset="100%" stop-color="#0f172a" stop-opacity="0.95"/>
        </linearGradient>
        <radialGradient id="hero-heart" cx="0.4" cy="0.4" r="0.65">
          <stop offset="0%" stop-color="#fb7185" stop-opacity="0.95"/>
          <stop offset="100%" stop-color="#9f1239" stop-opacity="0.45"/>
        </radialGradient>
        <radialGradient id="hero-brain" cx="0.4" cy="0.35" r="0.7">
          <stop offset="0%"  stop-color="#c4b5fd" stop-opacity="0.8"/>
          <stop offset="100%" stop-color="#5b21b6" stop-opacity="0.4"/>
        </radialGradient>
        <radialGradient id="hero-lung" cx="0.5" cy="0.3" r="0.8">
          <stop offset="0%"  stop-color="#67e8f9" stop-opacity="0.55"/>
          <stop offset="100%" stop-color="#0e7490" stop-opacity="0.3"/>
        </radialGradient>
        <radialGradient id="hero-liver" cx="0.3" cy="0.3" r="0.8">
          <stop offset="0%"  stop-color="#fbbf24" stop-opacity="0.55"/>
          <stop offset="100%" stop-color="#78350f" stop-opacity="0.3"/>
        </radialGradient>
        <radialGradient id="hero-stomach" cx="0.4" cy="0.3" r="0.8">
          <stop offset="0%"  stop-color="#fb923c" stop-opacity="0.55"/>
          <stop offset="100%" stop-color="#7c2d12" stop-opacity="0.3"/>
        </radialGradient>
        <filter id="hero-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      <!-- silhouette -->
      <g class="hero-silhouette">
        <ellipse cx="130" cy="56" rx="42" ry="46" fill="url(#hero-head)" stroke="#1e293b" stroke-width="1"/>
        <path d="M115 98 Q115 110 118 116 L142 116 Q145 110 145 98 Z" fill="url(#hero-skin)" stroke="#1e293b" stroke-width="1"/>
        <path
          d="M70 122 Q60 128 56 145 L42 188 Q38 240 64 256 L78 268 L86 280
             Q90 320 88 350 L86 410 Q84 440 82 480 L88 510 L100 512
             L108 480 Q108 440 110 410 Q112 360 116 320 L116 280 L144 280
             L144 320 Q148 360 150 410 Q152 440 152 480 L160 512 L172 510
             L178 480 Q176 440 174 410 L172 350 Q170 320 174 280 L182 268
             L196 256 Q222 240 218 188 L204 145 Q200 128 190 122
             Q160 110 130 110 Q100 110 70 122 Z"
          fill="url(#hero-skin)" stroke="#1e293b" stroke-width="1.2"
        />
        <path d="M58 144 Q40 158 30 220 Q26 260 32 290 Q38 308 44 300 Q46 280 50 250 Q56 200 70 158 Z"
              fill="url(#hero-skin)" stroke="#1e293b" stroke-width="1"/>
        <path d="M202 144 Q220 158 230 220 Q234 260 228 290 Q222 308 216 300 Q214 280 210 250 Q204 200 190 158 Z"
              fill="url(#hero-skin)" stroke="#1e293b" stroke-width="1"/>
      </g>

      <!-- vasculature with animated flow -->
      <g class="hero-vessels" opacity="0.55">
        <path d="M124 152 Q120 130 122 110" stroke="#dc2626" stroke-width="1.5" fill="none" opacity="0.6"/>
        <path d="M136 152 Q140 130 138 110" stroke="#dc2626" stroke-width="1.5" fill="none" opacity="0.6"/>
        <path d="M130 165 Q130 200 130 250 Q128 290 126 340"
              stroke="#dc2626" stroke-width="2" fill="none" class="hero-flow"/>
        <path d="M134 165 Q134 200 134 250 Q132 290 130 340"
              stroke="#1e40af" stroke-width="2" fill="none" opacity="0.55"/>
        <path d="M68 158 Q56 200 46 260" stroke="#dc2626" stroke-width="1" fill="none" opacity="0.45"/>
        <path d="M192 158 Q204 200 214 260" stroke="#dc2626" stroke-width="1" fill="none" opacity="0.45"/>
      </g>

      <!-- skeleton hints -->
      <g class="hero-skeleton" opacity="0.16">
        <path d="M82 158 Q130 152 178 158" stroke="#cbd5e1" stroke-width="1" fill="none"/>
        <path d="M78 175 Q130 168 182 175" stroke="#cbd5e1" stroke-width="1" fill="none"/>
        <path d="M76 192 Q130 185 184 192" stroke="#cbd5e1" stroke-width="1" fill="none"/>
        <path d="M78 210 Q130 203 182 210" stroke="#cbd5e1" stroke-width="1" fill="none"/>
        <line x1="130" y1="120" x2="130" y2="290" stroke="#cbd5e1" stroke-width="1.3"/>
      </g>

      <!-- organs (decorative, soft glow) -->
      <g class="hero-organs">
        <!-- brain -->
        <g class="hero-brain">
          <ellipse cx="130" cy="46" rx="28" ry="26" fill="url(#hero-brain)" filter="url(#hero-glow)"/>
          <path d="M108 42 Q122 36 134 42 Q146 36 154 44" stroke="#c4b5fd"
                stroke-width="0.7" fill="none" opacity="0.6"/>
          <path d="M108 52 Q122 46 134 52 Q146 46 154 54" stroke="#c4b5fd"
                stroke-width="0.7" fill="none" opacity="0.6"/>
        </g>

        <!-- heart -->
        <g class="hero-heart-beat">
          <path d="M122 142 C 114 132, 100 138, 104 154
                   C 108 168, 122 176, 130 182
                   C 138 176, 152 168, 156 154
                   C 160 138, 146 132, 138 142
                   C 134 138, 126 138, 122 142 Z"
                fill="url(#hero-heart)" filter="url(#hero-glow)"/>
        </g>

        <!-- lungs -->
        <g class="hero-lung-breath">
          <path d="M88 130 Q70 138 68 175 Q70 205 90 218 Q108 218 110 200 L110 140 Q104 128 88 130 Z"
                fill="url(#hero-lung)" filter="url(#hero-glow)"/>
          <path d="M172 130 Q190 138 192 175 Q190 205 170 218 Q152 218 150 200 L150 140 Q156 128 172 130 Z"
                fill="url(#hero-lung)" filter="url(#hero-glow)"/>
        </g>

        <!-- liver -->
        <path d="M88 222 Q86 218 100 218 L162 220 Q176 222 178 234
                 Q178 252 168 256 Q140 258 110 254 Q92 250 88 240 Z"
              fill="url(#hero-liver)" filter="url(#hero-glow)" opacity="0.85"/>

        <!-- stomach -->
        <path d="M110 248 Q102 252 102 264 Q104 280 116 282 Q132 284 146 278
                 Q156 272 154 258 Q152 248 142 246 Q124 244 110 248 Z"
              fill="url(#hero-stomach)" filter="url(#hero-glow)" opacity="0.85"/>
      </g>

      <!-- floating particles -->
      <g class="hero-particles">
        <circle r="1.5" fill="#60a5fa">
          <animateMotion dur="9s" repeatCount="indefinite"
                         path="M130 110 Q130 200 130 280 Q130 360 130 480"/>
          <animate attributeName="opacity" values="0;1;1;0" dur="9s" repeatCount="indefinite"/>
        </circle>
        <circle r="1.5" fill="#a78bfa">
          <animateMotion dur="11s" begin="2s" repeatCount="indefinite"
                         path="M70 160 Q50 240 40 320"/>
          <animate attributeName="opacity" values="0;0.8;0.8;0" dur="11s" begin="2s" repeatCount="indefinite"/>
        </circle>
        <circle r="1.5" fill="#a78bfa">
          <animateMotion dur="11s" begin="5s" repeatCount="indefinite"
                         path="M190 160 Q210 240 220 320"/>
          <animate attributeName="opacity" values="0;0.8;0.8;0" dur="11s" begin="5s" repeatCount="indefinite"/>
        </circle>
        <circle r="1.2" fill="#4ade80">
          <animateMotion dur="13s" begin="1s" repeatCount="indefinite"
                         path="M130 150 Q90 175 88 230"/>
          <animate attributeName="opacity" values="0;0.7;0.7;0" dur="13s" begin="1s" repeatCount="indefinite"/>
        </circle>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  reduceMotion?: boolean
}>()
</script>

<style scoped>
.hero-anatomy {
  position: relative;
  pointer-events: none;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hero-svg {
  width: 100%;
  max-width: 360px;
  height: auto;
  opacity: 0.78;
  filter: drop-shadow(0 30px 60px rgba(59,130,246,0.12));
}

.hero-heart-beat {
  transform-origin: 130px 162px;
  animation: hero-heart 1.2s ease-in-out infinite;
}
@keyframes hero-heart {
  0%, 100% { transform: scale(1); }
  20%      { transform: scale(1.08); }
  40%      { transform: scale(0.98); }
  60%      { transform: scale(1.05); }
}

.hero-lung-breath {
  transform-origin: 130px 174px;
  animation: hero-breath 4s ease-in-out infinite;
}
@keyframes hero-breath {
  0%, 100% { transform: scale(1); }
  50%      { transform: scale(1.05); }
}

.hero-brain {
  animation: hero-glow-brain 5s ease-in-out infinite;
}
@keyframes hero-glow-brain {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.85; }
}

.hero-flow {
  stroke-dasharray: 3 6;
  animation: hero-stream 14s linear infinite;
}
@keyframes hero-stream {
  0%   { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: -200; }
}

.reduce-motion .hero-heart-beat,
.reduce-motion .hero-lung-breath,
.reduce-motion .hero-flow,
.reduce-motion .hero-brain,
.reduce-motion .hero-particles {
  animation: none !important;
}
@media (prefers-reduced-motion: reduce) {
  .hero-heart-beat, .hero-lung-breath, .hero-flow, .hero-brain { animation: none !important; }
  .hero-particles { display: none; }
}
</style>
