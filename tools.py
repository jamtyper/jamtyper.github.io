import collections
import io
import json
import sys
import traceback

from browser import document
from browser import html
from browser import window


class Settings:

  def __init__(self, **defaults):
    self._values = defaults.copy()
    self._callbacks = collections.defaultdict(list)
    string = window.localStorage.getItem('settings')
    for key, value in json.loads(string or '{}').items():
      if key not in self._values:
        window.console.error(
            f"Found invalid settings key '{key}' in local storage.")
        continue
      self[key] = value
    window.localStorage.setItem('settings', json.dumps(self._values))

  @property
  def values(self):
    return self._values.copy()

  def __getitem__(self, key):
    return self._values[key]

  def __setitem__(self, key, value):
    assert key in self._values
    if self._values[key] == value:
      return
    self._values[key] = value
    window.localStorage.setItem('settings', json.dumps(self._values))
    for callback in self._callbacks[key]:
      callback(value)

  def bind(self, key, callback, now=False):
    now and callback(self[key])
    self._callbacks[key].append(callback)


class Actions:

  def __init__(self, editor):
    self._editor = editor
    self._actions = []
    self._keybinds = []

  def add(self, title, callback, button=None, keymap=None):
    self._actions.append((title, callback, button, keymap))
    buttons = document.select(button) if button else[]
    keydown = [callback]
    keyup = []
    for button in buttons:
      button.bind('click', lambda _: callback())
      keydown.append(lambda: button.classList.add('active'))
      keyup.append(lambda: button.classList.remove('active'))
      parent = button.parent if button.tagName == 'INPUT' else button
      text = title
      if keymap:
        text += f"<br><small>{keymap.replace('-', '–')}</small>"
      parent <= html.SPAN(text, Class='hint')
    if keymap:
      # Hide existing shortcuts in editor.
      self._editor.bind_key(keymap, lambda: None)
      self._keybinds.append(Keybind(document, keymap, keydown, keyup))


class Keybind:

  def __init__(self, element, key, keydown=None, keyup=None):
    keydown = keydown or ()
    keyup = keyup or ()
    self._key = key
    self._keydowns = keydown if hasattr(keydown, '__len__') else (keydown,)
    self._keyups = keyup if hasattr(keyup, '__len__') else (keyup,)
    self._down = False
    element.bind('keydown', self._keydown)
    document.bind('keyup', self._keyup)
    self._element = element

  def _keydown(self, event):
    if window.CodeMirror.keyName(event) != self._key:
      return
    event.preventDefault()
    if self._down:
      return
    self._down = True
    for callback in self._keydowns:
      callback()

  def _keyup(self, event):
    if window.CodeMirror.keyName(event).split('-')[-1] != self._key.split('-')[-1]:
      return
    if self._down:
      event.preventDefault()
      for callback in self._keyups:
        callback()
    self._down = False


class Logger:

  def __init__(self, element):
    self._element = element
    self._error = False

  def info(self, message):
    self._element.html += f'<p>{message}</p>'

  def error(self, message):
    window.console.error(message)
    if self._error:
      return
    self._error = True
    self._element.html += '<p>An error occured. Please open the ' \
        'developer tools for more information.</p>'

  def clear(self):
    self._error = False
    self._element.html = ''


def execute(source):
  orig_out = sys.stdout
  orig_err = sys.stderr
  stream = io.StringIO()
  sys.stdout = stream
  sys.stderr = stream
  success = None
  try:
    exec(source)
    success = True
  except Exception:
    traceback.print_exc()
    success = False
  sys.stdout = orig_out
  sys.stderr = orig_err
  return success, stream.getvalue()


def hsl_to_hex(h, s, l):
  l /= 100
  a = s * min(l, 1 - l) / 100
  def f(n):
    k = (n + h / 30) % 12
    color = l - a * max(min(k - 3, 9 - k, 1), -1)
    return round(255 * color)
  return f'#{f(0):02x}{f(8):02x}{f(4):02x}'
