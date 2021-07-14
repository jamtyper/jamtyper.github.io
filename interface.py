import json
import random

from browser import document
from browser import window

import jamtyper
import tools


class Interface:

  def __init__(self, settings, editor, logger):
    self._settings = settings
    self._editor = editor
    self._logger = logger
    self._actions = tools.Actions(self._editor)
    self._engine = window.Engine.new()
    self._editor.on('error', self._logger.error)
    # self._actions.add('New', self._new, '#create')
    # self._actions.add('Share', self._share, '#share')
    self._actions.add('Settings', self._settings_popup, '#settings')
    self._actions.add('Update', self._update, '#update', 'Ctrl-Enter')
    self._actions.add('Play', self._play, '#play', 'Ctrl-Space')
    # self._actions.add('Reset', lambda: self._time(0), '#reset', 'Ctrl-0')
    self._actions.add('Time', sel('#time').select, '#time', 'Ctrl-L')
    print('Keyboard shorcuts:', ''.join(
        f'\n- {x[0]} ({x[3]})' for x in self._actions._actions))
    sel('body').style.transition = 'background-color 10s ease'
    window.setTimeout(self._update_background, 0)
    window.setInterval(self._update_background, 10000)
    sel('#settings_input').addEventListener(
        'blur', lambda *_: self._update_settings())
    self._time(0)
    window.setInterval(self._tick, 100)
    tools.Keybind(sel('#time'), 'Enter', self._time)

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

  def _update_background(self):
    h = int(random.uniform(0, 360))
    s = int(random.uniform(20, 50))
    sel('body').style.background = f'hsl({h},{s}%,50%)'


def sel(selector, all=False):
  elements = document.select(selector)
  assert len(elements) == 1 or all, (selector, elements)
  return elements if all else elements[0]
