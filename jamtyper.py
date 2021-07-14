import json
from browser import window
import re


class AttrDict(dict):

  __getattr__ = dict.__getitem__


with open('scales.json') as f:
  scales = AttrDict({k: tuple(v) for k, v in json.load(f).items()})


samples = AttrDict(
    drums={
        'C4': 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/505/kick.ogg',
        'D4': 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/505/snare.ogg',
        'E4': 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/505/hho.ogg',
        'F4': 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/505/hh.ogg',
    },
    piano={
        'C1' : 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/C1.mp3',
        'F#1': 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/Fs1.mp3',
        'C2' : 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/C2.mp3',
        'F#2': 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/Fs2.mp3',
        'C3' : 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/C3.mp3',
        'F#3': 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/Fs3.mp3',
        'C4' : 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/C4.mp3',
        'F#4': 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/Fs4.mp3',
        'C5' : 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/C5.mp3',
        'F#5': 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/Fs5.mp3',
        'C6' : 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/C6.mp3',
        'F#6': 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/Fs6.mp3',
        'C7' : 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/C7.mp3',
        'F#7': 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/Fs7.mp3',
        'C8' : 'https://cdn.jsdelivr.net/gh/Tonejs/Tone.js/examples/audio/salamander/C8.mp3'
    }
)


DEFAULTS = dict(bpm=120, volume=1.0)
SETTINGS = DEFAULTS.copy()
players = []


def clear():
  """Clear all previous players to start a new song definition."""
  global players, SETTINGS
  players.clear()
  SETTINGS.clear()
  SETTINGS.update(DEFAULTS)


def settings(**kwargs):
  global SETTINGS
  for key, value in kwargs.items():
    assert key in DEFAULTS, key
    kwargs[key] = type(DEFAULTS[key])(value)
  if 'bpm' in kwargs:
    assert 1 <= kwargs['bpm'] <= 1000
  if 'volume' in kwargs:
    assert 0 <= kwargs['volume'] <= 5
  SETTINGS.update(kwargs)


def compile():
  """Get the song definition in JSON format."""
  global players, SETTINGS
  changes = []
  for index, player in enumerate(players):
    for change in player.changes:
      change = change.copy()
      change['track'] = index
      changes.append(change)
  song = dict(changes=changes, **SETTINGS)
  song = window.JSON.stringify(song)
  return song


class Player:

  # All properties also support lists of values that will be cycled between.

  defaults = {
      # General.
      'act': True,             # Whether the player is active.
      'dur': 1 / 4,            # Duration of each step in the loop.
      'cho': ('1',),           # Chord of note indices.
      'oct': 4,                # Octave offset in the scale.
      'sca': scales.c_major,   # Scale to map note index to freq or sample url.
      'len': 1 / 8,            # Length each note will be played for.

      # Instrument.
      'sam': {},               # Map from tones to sample URLs.
      'osc': 'triangle',       # Oscillator base shape for synth.
      'har': 0,                # Harmonies added to the base shape.
      'voi': 1,                # Number of voices for synth.
      'spr': 0.2,              # Spread between voices for synth.
      'atk': 0.1,              # Attack for synth.
      'dec': 0.2,              # Decay for synth.
      'sus': 1.0,              # Sustain for synth.
      'rel': 0.8,              # Release for synth.

      # Effects.
      'vol': 1.0,              # Volume or gain multiplier.
      'dly': 0.0,              # Delay time.
      'cpr': 0.0,              # Compressor threshold in decibels.
      'pan': 0.0,              # Panning between stereo channels.
      'hpf': 0,                # High pass filter threshold in Hertz.
      'lpf': 20000,            # Low pass filter threshold in Hertz.
      'rev': 0.0,              # Reverb room size.
      'bit': 0.0,              # Bit crusher.
      'low': 0.0,              # Equalizer lows in decibebls.
      'mid': 0.0,              # Equalizer mids in decibebls.
      'hig': 0.0,              # Equalizer highs in decibebls.
  }

  def __init__(self, **kwargs):
    global players
    players.append(self)
    self.changes = []
    self.at(0, **self.defaults)
    self.at(0, **kwargs)

  def at(self, start, stop=None, every=None, over=None, **kwargs):
    self._preprocess_state(kwargs)
    self._validate_state(kwargs)
    self.changes.append(dict(
        start=start, stop=stop, every=every, over=over, state=kwargs))

  def _preprocess_state(self, state):
    # for key, value in state.items():
    #   if not isinstance(value, list):
    #     state[key] = [value]
    for key, value in state.items():
      assert key in self.defaults, key
      default = self.defaults[key]
      # Turn everything into a list for unified processing.
      if not isinstance(value, list):
        value = [value]
      # value = value.copy() if isinstance(value, list) else [value]
      for index, item in enumerate(value):
        if isinstance(default, tuple):
          # Auto-wrap tuple attributes if given only one element.
          item = item if isinstance(item, tuple) else (item,)
          # Tuple attributes require deep type casting.
          item = [type(default[0])(x) for x in item]
        else:
          item = type(default)(item)
        value[index] = item
      state[key] = value
    # Property-specific preprocessing.
    if 'sam' in state:
      state['sam'] = [self._preprocess_sam(x) for x in state['sam']]
    if 'sca' in state:
      state['sca'] = [self._preprocess_sca(x) for x in state['sca']]

  def _preprocess_sam(self, sam):
    if isinstance(sam, dict):
      return sam
    if isinstance(sam, tuple):
      notes = 'CDEFGAB'
      output = {}
      for url in sam:
        tone = notes[len(sam) % len(notes)] + str(4 + len(sam) // len(notes))
        output[tone] = url
        return output
      raise TypeError

  def _preprocess_sca(self, sca):
    output = []
    octave = 0
    last = None
    notes = [
        'Cb', 'C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'E#', 'Fb', 'F',
        'F#', 'Gb', 'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B', 'B#']
    for note in sca:
      if any(str(x) in note for x in range(10)):
        groups = re.match(r'(.*)(-?[0-9]+)', note).groups()
        note = groups[0]
        octave = int(groups[1])
      else:
        if last and notes.index(note) <= notes.index(last):
          octave += 1
      output.append(f'{note}{octave}')
      last = note
    return tuple(output)

  def _validate_state(self, state):
    for key in state.keys():
      for single_value in state[key]:
        self._validate_state_variable(key, single_value)

  def _validate_state_variable(self, key, value):
    if key == 'cho':
      for index in value:
        assert re.search('^(-?[0-9]+)([#]*)([b]*)$', index)
    if key == 'sam':
      assert all(isinstance(key, str) for key in value.keys())
      assert all(isinstance(value, str) for value in value.values())
    if key == 'osc':
      assert value in ('sine', 'square', 'sawtooth', 'triangle')
    if key == 'har':
      assert 0 <= value <= 32
    if key == 'spr':
      assert 0.01 <= value <= 1
    if key == 'voi':
      assert 1 <= value <= 16
    if key in ['atk', 'dec', 'rel']:
      assert 0.001 <= value <= 10
    if key == 'sus':
      assert 0 <= value
    # if key == 'spe':
      # assert value in (-1, 1)
