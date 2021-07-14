from browser import document

import editor
import interface
import tools


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


def main():
  settings = tools.Settings(
      vim=False,
  )

  editor_ = editor.Editor(document.select('#editor')[0])
  editor_.set_text(EXAMPLE_SONG)
  settings.bind('vim', lambda x: editor_.set_settings(vim=x), now=True)

  logger = tools.Logger(document.select('#status')[0])

  interface.Interface(settings, editor_, logger)


main()
