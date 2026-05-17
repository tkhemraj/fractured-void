"""
Procedural sound generation — no audio files needed.
All sounds are synthesized from numpy waveforms at runtime.
Uses pygame.sndarray to convert numpy arrays into playable Sound objects.
"""
import numpy as np
import pygame

SAMPLE_RATE = 44100
CHANNELS = 2


def _to_stereo(mono: np.ndarray) -> np.ndarray:
    """Convert mono float32 array to 16-bit stereo."""
    clipped = np.clip(mono, -1.0, 1.0)
    s16 = (clipped * 32767).astype(np.int16)
    return np.column_stack([s16, s16])


def _make_sound(mono: np.ndarray) -> pygame.Sound:
    stereo = _to_stereo(mono)
    sound = pygame.sndarray.make_sound(stereo)
    return sound


def _envelope(samples: int, attack: float = 0.02, decay: float = 0.1, sustain: float = 0.7, release: float = 0.2) -> np.ndarray:
    n_attack  = int(samples * attack)
    n_decay   = int(samples * decay)
    n_sustain = int(samples * sustain)
    n_release = samples - n_attack - n_decay - n_sustain

    env = np.concatenate([
        np.linspace(0, 1, max(1, n_attack)),
        np.linspace(1, 0.7, max(1, n_decay)),
        np.full(max(1, n_sustain), 0.7),
        np.linspace(0.7, 0, max(1, n_release)),
    ])
    return env[:samples]


def gen_gun_fire() -> pygame.Sound:
    """Short kinetic crack — mass driver / laser bolt."""
    dur = 0.12
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    noise = np.random.randn(n) * 0.6
    tone = 0.4 * np.sin(2 * np.pi * 180 * t)
    wave = noise + tone
    env = np.exp(-25 * t)
    return _make_sound(wave * env * 0.8)


def gen_laser() -> pygame.Sound:
    """Laser cannon — pitched descending chirp."""
    dur = 0.15
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    freq = np.linspace(1200, 400, n)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    wave = 0.6 * np.sin(phase)
    env = np.exp(-18 * t)
    return _make_sound(wave * env)


def gen_neutron_gun() -> pygame.Sound:
    """Deep thump + high tone."""
    dur = 0.2
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    low = 0.5 * np.sin(2 * np.pi * 80 * t) * np.exp(-15 * t)
    high = 0.3 * np.sin(2 * np.pi * 2400 * t) * np.exp(-30 * t)
    return _make_sound(low + high)


def gen_missile_launch() -> pygame.Sound:
    """Rising whoosh."""
    dur = 0.35
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    freq = np.linspace(200, 900, n)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    tone = 0.4 * np.sin(phase)
    noise = 0.15 * np.random.randn(n)
    env = np.linspace(0, 1, n) * np.exp(-3 * t)
    return _make_sound((tone + noise) * env)


def gen_explosion_small() -> pygame.Sound:
    """Short burst hit."""
    dur = 0.25
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    noise = np.random.randn(n)
    # Low-pass: simple box filter
    kernel = np.ones(80) / 80
    filtered = np.convolve(noise, kernel, mode='same')
    env = np.exp(-12 * t)
    return _make_sound(filtered * env * 0.9)


def gen_explosion_large() -> pygame.Sound:
    """Big boom — ship destroyed."""
    dur = 1.2
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    noise = np.random.randn(n)
    kernel = np.ones(200) / 200
    filtered = np.convolve(noise, kernel, mode='same')
    low = 0.3 * np.sin(2 * np.pi * 60 * t)
    wave = filtered * 0.7 + low
    env = np.exp(-3 * t)
    return _make_sound(wave * env)


def gen_shield_hit() -> pygame.Sound:
    """Energy impact on shields — high metallic ring."""
    dur = 0.3
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    tone = 0.5 * np.sin(2 * np.pi * 800 * t)
    harmonic = 0.2 * np.sin(2 * np.pi * 1600 * t)
    env = np.exp(-10 * t)
    return _make_sound((tone + harmonic) * env)


def gen_warp() -> pygame.Sound:
    """Warp jump — frequency sweep down + deep thud."""
    dur = 0.8
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    freq = np.linspace(600, 60, n)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    sweep = 0.4 * np.sin(phase)
    noise = 0.15 * np.random.randn(n) * np.exp(-8 * t)
    env = _envelope(n, attack=0.05, decay=0.2, sustain=0.4, release=0.35)
    return _make_sound((sweep + noise) * env * 0.8)


def gen_hud_beep(high: bool = False) -> pygame.Sound:
    """Short UI confirmation beep."""
    dur = 0.08
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    freq = 1200 if high else 660
    wave = 0.3 * np.sin(2 * np.pi * freq * t)
    env = _envelope(n, attack=0.1, decay=0.0, sustain=0.6, release=0.3)
    return _make_sound(wave * env)


def gen_hud_alert() -> pygame.Sound:
    """Warning alert — two-tone pulse."""
    dur = 0.4
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    # Two alternating tones
    freq = np.where(np.floor(t * 8) % 2 == 0, 880, 660)
    wave = 0.35 * np.sin(2 * np.pi * freq * t)
    env = _envelope(n, attack=0.05, decay=0.1, sustain=0.6, release=0.25)
    return _make_sound(wave * env)


def gen_engine_hum() -> pygame.Sound:
    """Looping engine drone — combine at different volumes for speed."""
    dur = 1.0
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    fundamental = 0.25 * np.sin(2 * np.pi * 55 * t)
    harmonic2   = 0.15 * np.sin(2 * np.pi * 110 * t)
    harmonic3   = 0.08 * np.sin(2 * np.pi * 165 * t)
    # Slight vibrato
    lfo = 1 + 0.04 * np.sin(2 * np.pi * 5 * t)
    wave = (fundamental + harmonic2 + harmonic3) * lfo
    return _make_sound(wave)


def gen_trade_success() -> pygame.Sound:
    """Ascending three-note chime."""
    dur = 0.5
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    freqs = [523, 659, 784]
    note_len = n // 3
    wave = np.zeros(n)
    for i, freq in enumerate(freqs):
        start = i * note_len
        end = min(start + note_len, n)
        tn = t[start:end] - t[start]
        env = np.exp(-8 * tn)
        wave[start:end] += 0.3 * np.sin(2 * np.pi * freq * tn) * env
    return _make_sound(wave)


def gen_trade_fail() -> pygame.Sound:
    """Descending buzz — transaction rejected."""
    dur = 0.25
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    freq = np.linspace(400, 180, n)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    wave = 0.4 * np.sin(phase)
    env = np.exp(-6 * t)
    return _make_sound(wave * env)


def gen_mission_accept() -> pygame.Sound:
    """Dramatic three-note fanfare."""
    dur = 0.7
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    notes = [(0, 0.2, 440), (0.2, 0.4, 554), (0.4, 0.7, 659)]
    wave = np.zeros(n)
    for start_s, end_s, freq in notes:
        start = int(start_s * SAMPLE_RATE)
        end = int(end_s * SAMPLE_RATE)
        tn = t[start:end] - t[start]
        env = np.exp(-4 * tn)
        wave[start:end] += 0.35 * np.sin(2 * np.pi * freq * tn) * env
    return _make_sound(wave)


def gen_afterburner() -> pygame.Sound:
    """Quick acceleration burst."""
    dur = 0.3
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n)
    noise = 0.3 * np.random.randn(n)
    kernel = np.ones(30) / 30
    filtered = np.convolve(noise, kernel, mode='same')
    high = 0.2 * np.sin(2 * np.pi * np.linspace(300, 800, n) * t)
    env = np.linspace(0.5, 1.0, n) * np.exp(-4 * (t - dur)**2 * 20)
    return _make_sound((filtered + high) * env * 0.8)


class SoundManager:
    """Singleton that pre-generates all sounds and plays them on demand."""

    def __init__(self):
        self._sounds: dict[str, pygame.Sound] = {}
        self._engine_channel: pygame.mixer.Channel | None = None
        self._enabled = True
        self._initialized = False
        self._engine_playing = False

    def init(self) -> bool:
        if self._initialized:
            return True
        try:
            pygame.mixer.pre_init(frequency=SAMPLE_RATE, size=-16, channels=CHANNELS, buffer=512)
            pygame.mixer.init()
            self._build_sounds()
            self._engine_channel = pygame.mixer.Channel(0)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[Sound] Init failed: {e}")
            self._enabled = False
            return False

    def _build_sounds(self) -> None:
        builders = {
            "gun":             gen_gun_fire,
            "laser":           gen_laser,
            "neutron":         gen_neutron_gun,
            "missile":         gen_missile_launch,
            "explosion_small": gen_explosion_small,
            "explosion_large": gen_explosion_large,
            "shield_hit":      gen_shield_hit,
            "warp":            gen_warp,
            "beep_low":        lambda: gen_hud_beep(high=False),
            "beep_high":       lambda: gen_hud_beep(high=True),
            "alert":           gen_hud_alert,
            "engine":          gen_engine_hum,
            "trade_ok":        gen_trade_success,
            "trade_fail":      gen_trade_fail,
            "mission_accept":  gen_mission_accept,
            "afterburner":     gen_afterburner,
        }
        for name, fn in builders.items():
            try:
                self._sounds[name] = fn()
            except Exception as e:
                print(f"[Sound] Could not build '{name}': {e}")

    def play(self, name: str, volume: float = 1.0) -> None:
        if not self._enabled or name not in self._sounds:
            return
        try:
            snd = self._sounds[name]
            snd.set_volume(min(1.0, volume))
            snd.play()
        except Exception:
            pass

    def start_engine(self, volume: float = 0.15) -> None:
        if not self._enabled or not self._engine_channel or "engine" not in self._sounds:
            return
        if not self._engine_playing:
            self._sounds["engine"].set_volume(volume)
            self._engine_channel.play(self._sounds["engine"], loops=-1)
            self._engine_playing = True

    def update_engine(self, speed_ratio: float) -> None:
        if not self._enabled or not self._engine_channel:
            return
        vol = 0.05 + min(0.25, speed_ratio * 0.25)
        self._engine_channel.set_volume(vol)

    def stop_engine(self) -> None:
        if self._engine_channel:
            self._engine_channel.stop()
        self._engine_playing = False

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            pygame.mixer.stop()


sounds = SoundManager()
