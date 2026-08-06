let audio: HTMLAudioElement | null = null;

function getAudio(): HTMLAudioElement | null {
  if (typeof window === "undefined") return null;
  if (!audio) {
    audio = new Audio("/you-died.mp3");
    audio.volume = 0.9;
  }
  return audio;
}

/** Play the Dark Souls "YOU DIED" sting from dashboard/public/you-died.mp3. */
export function playThemeSwitchSound(): void {
  const a = getAudio();
  if (!a) return;
  // allow quick re-plays
  a.pause();
  a.currentTime = 0;
  void a.play().catch(() => {
    /* autoplay blocked — user gesture normally covers this */
  });
}