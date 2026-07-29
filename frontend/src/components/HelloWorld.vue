<template>
  <section class="landing-page">
    <div class="landing-bg-orb landing-bg-orb--left" />
    <div class="landing-bg-orb landing-bg-orb--right" />

    <header class="top-bar">
      <v-icon class="star-icon" icon="mdi-shimmer" size="22" />
      <div class="top-actions">
        <v-btn
          class="lang-btn"
          rounded="pill"
          variant="tonal"
          @click="toggleLanguage"
        >
          {{ localeLabel }}
        </v-btn>
        <v-btn class="avatar-btn" icon variant="tonal">
          <v-icon icon="mdi-account" size="18" />
        </v-btn>
        <v-btn class="login-btn" rounded="pill" variant="tonal">{{
          t(content.loginTextKey)
        }}</v-btn>
      </div>
    </header>

    <main class="hero-content">
      <h1 class="hero-title">{{ t(content.titleKey) }}</h1>
      <p class="hero-subtitle">{{ t(content.subtitleKey) }}</p>

      <div
        v-for="prompt in content.prompts"
        :key="prompt.id"
        class="prompt-pill"
        :class="prompt.positionClass"
      >
        <v-icon :icon="prompt.icon ?? 'mdi-waveform'" size="18" />
        <span>{{ t(prompt.textKey) }}</span>
      </div>

      <div class="mic-wrap">
        <div class="mic-core">
          <v-icon icon="mdi-microphone" size="92" />
        </div>
      </div>

      <v-btn
        class="upload-btn bg-accent"
        color="accent"
        prepend-icon="mdi-folder-plus-outline"
        rounded="pill"
        size="x-large"
      >
        {{ t(content.uploadTextKey) }}
      </v-btn>
    </main>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { useI18n } from 'vue-i18n'

  import { landingContent } from '@/constants/landing-content'

  const { t, locale } = useI18n()
  const content = landingContent

  const localeLabel = computed(() =>
    locale.value === 'zh-TW' ? 'EN' : '中文',
  )

  function toggleLanguage () {
    locale.value = locale.value === 'zh-TW' ? 'en' : 'zh-TW'
    localStorage.setItem('locale', locale.value)
  }
</script>

<style>
  @reference "../styles/tailwind.css";

  .landing-page {
    @apply relative min-h-[calc(100vh-64px)] overflow-hidden px-6 py-6 sm:px-10;
    background: linear-gradient(180deg, #d7e6fb 0%, #cfdff3 45%, #c8d8ec 100%);
  }

  .landing-bg-orb {
    position: absolute;
    border-radius: 9999px;
    pointer-events: none;
    filter: blur(2px);
    opacity: 0.95;
  }

  .landing-bg-orb--left {
    width: 640px;
    height: 360px;
    left: -180px;
    top: 290px;
    background: radial-gradient(
      circle at 50% 45%,
      rgba(17, 103, 255, 0.72) 0%,
      rgba(17, 103, 255, 0) 72%
    );
  }

  .landing-bg-orb--right {
    width: 680px;
    height: 420px;
    right: -170px;
    top: 250px;
    background: radial-gradient(
      circle at 50% 45%,
      rgba(0, 100, 255, 0.8) 0%,
      rgba(0, 100, 255, 0) 72%
    );
  }

  .top-bar {
    @apply relative z-10 flex items-center justify-between;
  }

  .star-icon {
    color: #1362d9;
  }

  .top-actions {
    @apply flex items-center gap-2;
  }

  .lang-btn {
    @apply px-4;
    min-width: 68px;
    background: rgba(255, 255, 255, 0.35);
    color: #1f4f9f;
    font-weight: 700;
  }

  .avatar-btn {
    background: rgba(255, 255, 255, 0.35);
    color: #1f4f9f;
  }

  .login-btn {
    @apply px-6;
    background: rgba(255, 255, 255, 0.35);
    color: #1f4f9f;
  }

  .hero-content {
    @apply relative z-10 mx-auto mt-16 flex max-w-[980px] flex-col items-center;
  }

  .hero-title {
    @apply m-0 text-center text-[42px] font-bold tracking-tight text-[#0c53cb] sm:text-[64px];
  }

  .hero-subtitle {
    @apply mt-3 text-center text-[28px] text-[#165fce];
  }

  .prompt-pill {
    @apply absolute flex items-center gap-2 rounded-[999px] px-7 py-4 text-[20px] font-semibold text-[#1b458f] shadow-lg;
    background: rgba(232, 244, 255, 0.72);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.75),
      0 8px 18px rgba(27, 70, 139, 0.14);
  }

  .prompt-pill--left-top {
    left: 0;
    top: 185px;
  }

  .prompt-pill--right {
    right: 0;
    top: 240px;
  }

  .prompt-pill--left-bottom {
    left: 70px;
    top: 370px;
  }

  .mic-wrap {
    @apply mt-20 flex h-[230px] w-[230px] items-center justify-center rounded-[999px];
    background: radial-gradient(
      circle at 50% 72%,
      #b5fae7 0%,
      #9dc0f8 52%,
      #8fb7f4 100%
    );
    box-shadow:
      inset 0 2px 20px rgba(255, 255, 255, 0.45),
      0 14px 28px rgba(33, 90, 172, 0.2);
  }

  .mic-core {
    @apply flex h-[170px] w-[170px] items-center justify-center rounded-[999px] text-white;
    background: linear-gradient(
      180deg,
      rgba(255, 255, 255, 0.08) 0%,
      rgba(24, 97, 190, 0.25) 100%
    );
  }

  .upload-btn {
    @apply mt-14 px-16 text-[36px] font-bold;
    min-height: 74px;
    letter-spacing: 0;
  }

  @media (max-width: 960px) {
    .hero-content {
      @apply mt-10;
    }

    .hero-subtitle {
      @apply text-[24px];
    }

    .prompt-pill {
      position: static;
      @apply mt-4 w-full max-w-[420px] justify-center text-[18px];
    }

    .mic-wrap {
      @apply mt-8;
    }

    .upload-btn {
      @apply mt-10 text-[26px];
      min-height: 62px;
    }
  }
</style>
