<!--
  AnatomyHero.vue — home page decorative anatomy figure (v6.0)
  Base image: full-color anatomy PNG provided by team (public/anatomy-hero.png)
  SVG overlay: scan lines + particles + heart/brain pulse rings + HUD corner labels
-->
<template>
  <div class="hero-anatomy" :class="{ 'reduce-motion': reduceMotion }">
    <svg viewBox="0 0 420 840" xmlns="http://www.w3.org/2000/svg" class="hero-svg">
      <defs>
        <!-- Scan gradient — cyan theme matching PNG -->
        <linearGradient id="scan-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"    stop-color="#00d4ff" stop-opacity="0"/>
          <stop offset="45%"   stop-color="#00d4ff" stop-opacity="0"/>
          <stop offset="48.5%" stop-color="#7df4ff" stop-opacity="0.09"/>
          <stop offset="49.6%" stop-color="#e0ffff" stop-opacity="0.88"/>
          <stop offset="50.4%" stop-color="#7df4ff" stop-opacity="0.35"/>
          <stop offset="54%"   stop-color="#00d4ff" stop-opacity="0"/>
          <stop offset="100%"  stop-color="#00d4ff" stop-opacity="0"/>
        </linearGradient>
      </defs>

      <!-- ── Base: anatomy PNG ── -->
      <image href="/anatomy-hero.png" x="0" y="0" width="420" height="840"
             preserveAspectRatio="xMidYMid meet" class="body-img"/>

      <!-- ── Scan line sweep ── -->
      <rect class="scan-line" x="0" y="0" width="420" height="840"
            fill="url(#scan-grad)" opacity="0.85"/>

      <!-- ── Pulse rings: heart ── -->
      <circle cx="197" cy="272" fill="none" stroke="#fda4af" stroke-width="0.9">
        <animate attributeName="r"        values="24;40;56"    dur="1.15s" repeatCount="indefinite"/>
        <animate attributeName="opacity"  values="0.55;0.15;0" dur="1.15s" repeatCount="indefinite"/>
      </circle>

      <!-- ── Pulse rings: brain ── -->
      <circle cx="210" cy="108" fill="none" stroke="#a78bfa" stroke-width="0.8">
        <animate attributeName="r"        values="36;58;80"    dur="3.2s"  repeatCount="indefinite"/>
        <animate attributeName="opacity"  values="0.4;0.12;0"  dur="3.2s"  repeatCount="indefinite"/>
      </circle>

      <!-- ── Particles ── -->
      <g class="particles">
        <!-- Central aorta flow -->
        <circle r="2.2" fill="#00d4ff" opacity="0.9">
          <animateMotion dur="8s" repeatCount="indefinite"
            path="M210 190 Q210 310 210 430 Q209 530 208 670"/>
          <animate attributeName="opacity" values="0;0.9;0.9;0" dur="8s" repeatCount="indefinite"/>
        </circle>
        <!-- Left side / pulmonary -->
        <circle r="1.8" fill="#a78bfa">
          <animateMotion dur="11s" begin="2s" repeatCount="indefinite"
            path="M155 210 Q132 280 128 365 Q124 420 130 480"/>
          <animate attributeName="opacity" values="0;0.8;0.8;0" dur="11s" begin="2s" repeatCount="indefinite"/>
        </circle>
        <!-- Right side / pulmonary -->
        <circle r="1.8" fill="#a78bfa">
          <animateMotion dur="11s" begin="5.5s" repeatCount="indefinite"
            path="M265 210 Q288 280 292 365 Q296 420 290 480"/>
          <animate attributeName="opacity" values="0;0.8;0.8;0" dur="11s" begin="5.5s" repeatCount="indefinite"/>
        </circle>
        <!-- Cardiac → hepatic -->
        <circle r="1.5" fill="#4ade80">
          <animateMotion dur="13s" begin="1s" repeatCount="indefinite"
            path="M200 248 Q182 278 172 335"/>
          <animate attributeName="opacity" values="0;0.75;0.75;0" dur="13s" begin="1s" repeatCount="indefinite"/>
        </circle>
        <!-- Circulation loop -->
        <circle r="1.5" fill="#f87171">
          <animateMotion dur="9s" begin="3s" repeatCount="indefinite"
            path="M215 270 Q234 282 250 318 Q258 355 245 390"/>
          <animate attributeName="opacity" values="0;0.75;0.75;0" dur="9s" begin="3s" repeatCount="indefinite"/>
        </circle>
      </g>

      <!-- ── HUD corner brackets ── -->
      <g class="hud-brackets" opacity="0.5">
        <path d="M10 10 L10 32 M10 10 L32 10"   stroke="#00d4ff" stroke-width="1.8" fill="none"/>
        <path d="M410 10 L388 10 M410 10 L410 32" stroke="#00d4ff" stroke-width="1.8" fill="none"/>
        <path d="M10 830 L10 808 M10 830 L32 830"   stroke="#00d4ff" stroke-width="1.8" fill="none"/>
        <path d="M410 830 L388 830 M410 830 L410 808" stroke="#00d4ff" stroke-width="1.8" fill="none"/>
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
  max-width: 260px;
  height: auto;
  filter: drop-shadow(0 0 40px rgba(0, 212, 255, 0.25))
          drop-shadow(0 0 90px rgba(0, 212, 255, 0.10));
}

/* Scan sweep */
.scan-line {
  animation: scan-sweep 5s linear infinite;
}
@keyframes scan-sweep {
  0%   { transform: translateY(-840px); }
  100% { transform: translateY(840px); }
}

/* HUD blink */
.hud-brackets {
  animation: hud-blink 4s ease-in-out infinite;
}
@keyframes hud-blink {
  0%, 88%, 100% { opacity: 0.5; }
  94%           { opacity: 0.85; }
}

/* Subtle breathe on whole image */
.body-img {
  animation: img-breathe 5s ease-in-out infinite;
}
@keyframes img-breathe {
  0%, 100% { opacity: 0.92; }
  50%       { opacity: 1; }
}

/* Reduced motion */
.reduce-motion .scan-line,
.reduce-motion .hud-brackets,
.reduce-motion .body-img,
.reduce-motion .particles { animation: none !important; }

@media (prefers-reduced-motion: reduce) {
  .scan-line, .hud-brackets, .body-img { animation: none !important; }
  .particles { display: none; }
}
</style>
