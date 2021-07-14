from browser import window


class Editor:

  def __init__(self, element, **kwargs):
    self._settings = dict(vim=False)
    self._keybinds = {}
    self._listeners = {}
    self._element = element
    self._cm = window.CodeMirror.new(element, dict(
        lineNumbers=True, matchBrackets=True, tabSize=2, theme='gruvbox-dark',
        inputStyle='textarea', lineWrapping=True))
    self.bind_key('Tab', self._tab)
    self.bind_key('Ctrl-/', lambda: self._cm.execCommand('toggleComment'))
    self.set_settings(**kwargs)

  def on(self, event, callback):
    assert event in ('error',)
    if event not in self._listeners:
      self._listeners[event] = []
    self._listeners[event].append(callback)

  def get_text(self):
    return self._cm.getValue()

  def set_text(self, text):
    return self._cm.setValue(text)

  def get_settings(self):
    return self._settings.copy()

  def set_settings(self, **kwargs):
    for key in kwargs:
      assert key in self._settings, key
    self._settings.update(kwargs)
    self._cm.setOption('vimMode', self._settings['vim'])

  def bind_key(self, key, callback):
    key = key.replace('Control', 'Ctrl')
    self._keybinds[key] = lambda _: callback()
    self._cm.setOption('extraKeys', self._keybinds)

  def open(self, name, success=None, failure=None):
    window.console.log('load', name)

  def _error(self, error):
    if not error:
      return
    if not self._listeners['error']:
      window.console.error(error)
    for callback in self._listeners['error']:
      callback(error)

  def _tab(self):
    if self._cm.somethingSelected():
      self._cm.indentSelection('add')
    else:
      self._cm.replaceSelection(' ' * self._cm.getOption('indentUnit'))

  def _sanitize_change(self, _, change):
    change.text = [
        line.encode('ascii', errors='ignore').decode()
        for line in change.text]
