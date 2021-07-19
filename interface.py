import json
import random

from browser import document
from browser import window

import jamtyper
import tools


DATABASE_URL = 'https://jamtyper-969f2-default-rtdb.firebaseio.com/songs/data'

EXAMPLE_SONG = """
import random
import jamtyper as jt

jt.settings(bpm=120, volume=1.0)

drums = jt.Player(cho=[0,3,1,3], dur=1/8, sam=jt.samples.drums)
drums.at(16, cho=[0,3,(1,2),3], vol=[1.5,1,1,1])

hat = jt.Player(
  cho=(), dur=1/8, len=1/10, sam=jt.samples.drums, vol=0.6,
  hpf=2000, lpf=6000, pan=[-1,1])
hat.at(8, cho=2)
hat.at(12, vol=0)

lead = jt.Player(
  cho=[0,1,2,3,4,5,6,7], dur=[1/4,1/8], sca=jt.scales.e_major,
  vol=0.3, atk=0.01, lpf=1000)
lead.at(24, vol=0)

rando = jt.Player(
  cho=[random.randint(0, 4) for _ in range(100)],
  dur=[random.choice([1/4,1/8,1/8]) for _ in range(100)],
  sca=jt.scales.e_major_penta, vol=0.3, hpf=1000)
rando.at(24, vol=0.6, hpf=0)
""".strip('\n ')

MESSAGE_SAVED = """
Song saved under the following URL. You can bookmark this link or share it with
your friends! <a class="url" href="{0}">{0}</a>
"""


class Interface:

  def __init__(self, settings, editor, logger):
    self._settings = settings
    self._editor = editor
    self._logger = logger
    self._actions = tools.Actions(self._editor)
    self._bind_ux_events()
    self._engine = window.Engine.new()
    self._time(0)
    window.setInterval(self._tick, 100)
    self._animate_background()
    if window.location.hash.strip('#') not in ('', 'unsaved'):
      self._load()
    else:
      self._new()
    window.addEventListener('hashchange', lambda *_: self._load)

  def _bind_ux_events(self):
    self._editor.on('error', self._logger.error)
    self._actions.add('New', self._new, '#new')
    self._actions.add('Save', self._save, '#save')
    self._actions.add('Settings', self._settings_popup, '#settings')
    self._actions.add('Update', self._update, '#update', 'Ctrl-Enter')
    self._actions.add('Play', self._play, '#play', 'Ctrl-Space')
    # self._actions.add('Reset', lambda: self._time(0), '#reset', 'Ctrl-0')
    self._actions.add('Time', sel('#time').select, '#time', 'Ctrl-L')
    tools.Keybind(sel('#time'), 'Enter', self._time)
    sel('#settings_input').addEventListener(
        'blur', lambda *_: self._update_settings())
    print('Keyboard shorcuts:', ''.join(
        f'\n- {x[0]} ({x[3]})' for x in self._actions._actions))

  def _new(self):
    self._logger.clear()
    self._editor.set_text(EXAMPLE_SONG)
    window.location.hash = 'unsaved'
    self._logger.info('Started a new song.')
    self._update()

  def _load(self):
    self._logger.clear()
    key = window.location.hash.strip('#')
    def callback(data):
      # window.console.log(data)
      self._editor.set_text(data['content'])
      self._update()
    window.fetch(DATABASE_URL + f'/{key}.json', {
        'method': 'GET',
        'mode': 'cors',
    }) \
        .then(lambda resp: resp.json()) \
        .then(callback) \
        .catch(self._logger.error)

  def _save(self):
    self._logger.clear()
    def callback(data):
      # window.console.log(data)
      window.location.hash = data['name']
      sel('#editor textarea').focus()
      url = 'https://jamtyper.com/#' + data['name']
      self._logger.info(MESSAGE_SAVED.format(url))
    window.fetch(DATABASE_URL + '.json', {
        'method': 'POST',
        'mode': 'cors',
        'body': window.JSON.stringify({'content': self._editor.get_text()}),
    }) \
        .then(lambda resp: resp.json()) \
        .then(callback) \
        .catch(self._logger.error)

  def _update(self):
    sel('#editor textarea').focus()
    jamtyper.clear()
    success, output = tools.execute(self._editor.get_text())
    if success:
      sel('#flash').classList.add('success')
      window.setTimeout(lambda: sel('#flash').classList.remove('success'), 200)
      song = jamtyper.compile()
      self._engine.update(song)
    else:
      sel('#flash').classList.add('error')
      window.setTimeout(lambda: sel('#flash').classList.remove('error'), 200)
    sel('#output pre').textContent = output
    sel('#output').style.display = ['none', 'flex'][int(bool(output.strip()))]
    sel('#output pre').scrollTop = sel('#output pre').scrollHeight

  def _time(self, time=None):
    sel('#editor textarea').focus()
    if time is None:
      time = sel('#time').value
    self._engine.time = round(float(time), 2)
    sel('#time').value = f'{self._engine.time:.2f}'

  def _tick(self):
    if sel('#time') != document.activeElement:
      sel('#time').value = f'{self._engine.time:.2f}'

  def _play(self):
    sel('#editor textarea').focus()
    if self._engine.playing():
      self._engine.pause()
      sel('#play').classList.remove('pause')
      sel('#play').classList.add('play')
    else:
      self._engine.play()
      sel('#play').classList.remove('play')
      sel('#play').classList.add('pause')

  def _settings_popup(self):
    if 'active' not in sel('#settings').classList:
      sel('#settings').classList.add('active')
      sel('#settings_input').value = json.dumps(self._settings.values)
      sel('#settings_popup').style.display = 'inline-block'
    else:
      sel('#settings').classList.remove('active')
      sel('#settings_popup').style.display = 'none'

  def _update_settings(self):
    try:
      for key, value in json.loads(sel('#settings_input').value).items():
        self._settings[key] = value
    except Exception as e:
      self._logger.error(e)
    print('Settings updated:', self._settings.values)

  def _animate_background(self):
    sel('body').style.transition = 'background-color 10s ease'
    window.setTimeout(self._update_background, 0)
    window.setInterval(self._update_background, 10000)

  def _update_background(self):
    h = int(random.uniform(0, 360))
    s = int(random.uniform(20, 50))
    sel('body').style.background = f'hsl({h},{s}%,50%)'


def sel(selector, all=False):
  elements = document.select(selector)
  assert len(elements) == 1 or all, (selector, elements)
  return elements if all else elements[0]
