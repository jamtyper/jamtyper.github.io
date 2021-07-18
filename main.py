from browser import document

import editor
import interface
import tools


def main():
  settings = tools.Settings(
      vim=False,
  )

  editor_ = editor.Editor(document.select('#editor')[0])
  settings.bind('vim', lambda x: editor_.set_settings(vim=x), now=True)

  logger = tools.Logger(document.select('#status')[0])

  interface.Interface(settings, editor_, logger)


main()
