const tone = window.Tone

/*****************************************************************************/
// Standard functions
/*****************************************************************************/

function uniq(elements) {
  return sorted([... new Set(elements)])
}

function zip(a, b) {
    const zipped = []
    for (let i = 0; i < Math.min(a.length, b.length); i++)
      zipped.push([a[i], b[i]])
    return zipped
}

function lookup(arr, index) {
  if (index < 0)
    return arr[arr.length - index]
  return arr[index]
}

function slice(arr, start, stop) {
  start = start === null ? 0 : start
  stop = stop === null ? arr.length : stop
  start = start < 0 ? arr.length - start : start
  stop = stop < 0 ? arr.length - stop : stop
  return arr.slice(start, stop)
}

function enumerate(arr) {
    return arr.map((elem, idx) => [idx, elem])
}

function sorted(arr) {
  return arr.sort((a, b) => a - b)
}

function jsonEqual(a, b) {
  return JSON.stringify(a) === JSON.stringify(b)
}

function sum(coll) {
  return coll.reduce((a, b) => a + b, 0)
}

function modulo(value, size) {
  return ((value % size) + size) % size
}

/*****************************************************************************/
// Sound helpers
/*****************************************************************************/

function ratioToDecibels(ratio) {
  return 10 * Math.log10(ratio)
}

function decibelsToRatio(decibels) {
  return 10 ** (decibels / 10)
}

function disconnectOutputs(audioNode) {
  for (let i = 0; i < audioNode.numberOfOutputs; i++)
    audioNode.disconnect(i)
}

/*****************************************************************************/
// Sound engine
/*****************************************************************************/

const JAMTYPER_LOOK_AHEAD = 0.5


class Engine {

  constructor() {
    this.time = 0
    this._song = null
    this._instruments = new Map()
    this._sample_cache = new Map()
    // tone.context.latencyHint = 'playback'
    tone.context.lookAhead = 0.5
    tone.Transport.cancel()
    this._loop = this._loop.bind(this)
    tone.Transport.scheduleRepeat(
      this._loop, JAMTYPER_LOOK_AHEAD + ':0:0')
  }

  playing() {
    return tone.Transport.state == 'started'
  }

  update(definition) {
    const song = JSON.parse(definition)
    const tracks = uniq(song['changes'].map(change => change['track']))
    const old = new Map(this._instruments)
    setTimeout(() => {
      this._song = song
      // Load sample files. Later, we can have this function block until they
      // are loaded, so they song does not start early.
      for (let change of song['changes']) {
        if (change['state'].hasOwnProperty('sam')) {
          for (let sam of change['state']['sam']) {
            for (let [key, url] of Object.entries(sam)) {
              if (!this._sample_cache.has(url)) {
                let buffer = new tone.ToneAudioBuffer(url)
                buffer.url = url
                this._sample_cache.set(url, buffer)
              }
              let buffer = this._sample_cache.get(url)
              change['state']['sam'][key] = buffer
      }}}}
      console.log('Updated song.')
      // Replace the sound instruments.
      this._instruments = new Map(tracks.map(track => [track, new Instrument()]))
      tone.Transport.bpm.value = song['bpm']
      tone.Destination.volume.value = ratioToDecibels(song['volume'])
      setTimeout(() => {
        for (let instrument of old.values())
          instrument.close()
      }, 5000)
    }, 0)
  }

  toggle() {
    tone.start()
    tone.Transport.toggle('+0.01')
  }

  play() {
    tone.start()
    tone.Transport.start('+0.01')
  }

  pause() {
    tone.start()
    tone.Transport.pause('+0.01')
  }

  _loop(pulse) {
    for (let [track, instrument] of this._instruments.entries()) {
      const events = this._query(track, this.time, this.time + JAMTYPER_LOOK_AHEAD)
      for (let [time, state] of events) {
        const offset = tone.Transport.toSeconds((time - this.time) + ':0:0')
        instrument.call(pulse + offset, state)
      }
    }
    this.time += JAMTYPER_LOOK_AHEAD
  }

  _query(track, start, stop) {
    // Returns the sound events that occur within a time frame. We traverse the
    // time frame in non-overlapping intervals. When an interval contains a
    // note, it is added to the result list. The interval boundaries are
    // initialized to the times of state changes. For each interval, we step
    // through the active loop to find any notes inside the interval.
    const events = []
    const times = uniq([start, stop].concat(this._get_events(track, start, stop)))
    for (let [lhs, rhs] of zip(slice(times, 0, -1), slice(times, 1, null))) {
      const [state, since] = this._get_state(track, lhs)
      const dur = Array.isArray(state['dur']) ? state['dur'] : [state['dur']]
      // To compute the loop index, we see how many notes have been played
      // since the duration property was changed the last time.
      let completed = Math.floor((start - since['dur']) / sum(dur))
      let time = since['dur'] + completed * sum(dur)
      let index = completed * dur.length
      while (time < rhs) {
        // console.log(time, rhs)
        if (lhs - 1e-6 <= time && time < rhs) {
          let prepared = Object.assign({}, state)
          // for (let [key, value] of Object.entries(prepared))
          //   if (Array.isArray(value))
          //     prepared[key] = value[index % value.length]
          for (let [key, value] of Object.entries(prepared))
            prepared[key] = value[index % value.length]
          if (prepared['act'] && prepared['cho'] && prepared['cho'].length > 0)
            events.push([time, prepared])
        }
        time += dur[index % dur.length]
        index += 1
      }
    }
    return events
  }

  _get_events(track, start, stop) {
    const events = []
    for (let change of this._song['changes']) {
      if (change['track'] != track)
        continue
      if (start <= change['start'] && change['start'] < stop)
        events.push(change['start'])
      if (change['stop'] !== null && start <= change['stop'] && change['stop'] < stop)
        events.push(change['stop'])
      if (change['every']) {
        // Step through the period to find all state changes.
        let time = start - (start - change['start']) % change['every']
        while (time < stop) {
          if (start <= time && time < stop)
            events.push(time)
          if (start <= time + change['over'] && time + change['over'] < stop)
            events.push(time + change['over'])
          time += change['every']
        }
      }
    }
    return events
  }

  _get_state(track, time) {
    let state = {}
    let since = {}
    for (let change of this._song['changes']) {
      if (change['track'] != track)
        continue
      if (time < change['start'])
        continue
      if (change['stop'] !== null && time >= change['stop'])
        continue
      if (change['every'] !== null) {
        const over = change['over'] === null ? change['every'] : change['over']
        if ((time - change['start']) % change['every'] >= over)
          continue
      }
      for (let key in change['state']) {
        state[key] = change['state'][key]
        since[key] = change['start']
      }
    }
    return [state, since]
  }
}


/*****************************************************************************/
// Instruments
/*****************************************************************************/


class Instrument {

  constructor() {
    this._synths = {}
    this._samplers = {}
    this._effects = new EffectChain()
    this._effects.output.connect(tone.Destination)
  }

  call(pulse, state) {
    this._effects.call(pulse, state)
    const tones = []
    for (let index of state['cho'])
      tones.push(this._scale(index, state['oct'], state['sca']))
    let inst = null
    if (jsonEqual(state['sam'], {})) {
      inst = this._get_synth(state)
    } else {
      inst = this._get_sampler(state)
      if (!inst.loaded) {
        console.log('Skipping samples that are still being loaded.')
        return
      }
    }
    inst.triggerAttackRelease(tones, state['len'] + ':0:0', pulse)
  }

  _get_synth(state) {
    const props = ['osc', 'atk', 'dec', 'sus', 'rel', 'har', 'voi', 'spr']
    const key = props.map(key => state[key]).join(',')
    if (!this._synths.hasOwnProperty(key)) {
      this._synths[key] = new tone.PolySynth()
      let type = state['osc']
      if (state['voi'] > 1) type = 'fat' + type
      if (state['har'] > 0) type = type + state['har'].toString()
      this._synths[key].set({
        oscillator: {
          type: type,
          count: state['voi'],
          spread: 100 * state['spr'],
        },
        envelope: {
          attack: state['atk'],
          decay: state['dec'],
          sustain: state['sus'],
          release: state['rel'],
        }
      })
      this._synths[key].connect(this._effects.input)
    }
    return this._synths[key]
  }

  _get_sampler(state) {
    const samHash = Object.keys(state['sam']).sort().map(
        k => `'${k}':'${state['sam'][k]}'`).join(',')
    const key = [state['atk'], state['rel'], samHash]
    if (!this._samplers.hasOwnProperty(key)) {
      // TODO: Attack doesn't seem to be applied.

      // const urls = {}
      // for (const key of Object.keys(state['sam']))
      //   urls[key] = new tone.ToneAudioBuffer(state['sam'][key])

      this._samplers[key] = new tone.Sampler({
          urls: state['sam'], attack: state['atk'], release: state['rel']})
      this._samplers[key].connect(this._effects.input)
    }
    return this._samplers[key]
  }

  _scale(index, octave, scale) {
    const match = index.match(/^(-?[0-9]+)([#]*)([b]*)$/)
    const baseIndex = parseInt(match[1])
    const semitones = match[2].length - match[3].length
    const note = scale[modulo(baseIndex, scale.length)]
    if (!(typeof note === 'string'))
      return note
    const [baseNote, baseOct] = slice(note.match(/^(.*)(-?[0-9])$/), 1)
    // The octave is determined by the base octave in the sacle, the oct
    // property of the state, and by how much the note index is out of range.
    const wrapOct = Math.floor(parseFloat((baseIndex) / scale.length))
    octave = parseInt(baseOct) + octave + wrapOct
    return tone.Frequency(baseNote + octave.toString()).transpose(semitones)
  }

  close() {
    for (let synth in this._synths)
      (synth.close === 'function') && synth.close()
    for (let sampler in this._samplers)
      (sampler.close === 'function') && sampler.close()
    this._effects.close()  // This was commented out before?
  }
}


/*****************************************************************************/
// Effects
/*****************************************************************************/


class EffectChain {

  constructor() {
    this._chain = [
      // new Equalizer(),
      new Filter(),
      // new Reverb(),
      new Delay(),
      new Volume(),
      new Panner(),
      new Compressor(),
    ]
    for (let [index, effect] of enumerate(this._chain))
      this._chain[index] = new AutoDisconnect(new AutoSkip(effect))
    for (let [lhs, rhs] of zip(slice(this._chain, null, -1), slice(this._chain, 1, null)))
      lhs.output.connect(rhs.input)
    this.input = this._chain[0].input
    this.output = this._chain[this._chain.length - 1].output
  }

  defaults() {
    const defaults = {}
    for (let effect of this._chain)
      defaults.update(effect.defaults)
    return defaults
  }

  call(pulse, state) {
    for (let effect of this._chain)
      effect.call(pulse, state)
  }

  close() {
    for (let effect of this._chain)
      effect.close()
  }
}


class AutoDisconnect {

  constructor(effect) {
    this.input = new tone.Gain()
    this.output = new tone.Gain()
    this.input.connect(this.output)
    this._effect = effect
    this._effect.output.connect(this.output)
    this.timeout = null
    this._was_needed = false
  }

  defaults() {
    return this._effect.defaults()
  }

  call(pulse, state) {
    const now_needed = this._needed(state)
    if (!this._was_needed && !now_needed)
      return
    if (this._was_needed && !now_needed)
      this.timeout = setTimeout(() => this.input.disconnect().connect(this.output), 2000)
    if (!this._was_needed && now_needed) {
      if (this.timeout)
        clearTimeout(this.timeout)
      this.timeout = null
      this.input.disconnect().connect(this._effect.input)
    }
    this._was_needed = now_needed
    this._effect.call(pulse, state)
  }

  close() {
    this.input.dispose()
    this.output.dispose()
    this._effect.close()
  }

  _needed(state) {
    for (let [key, value] of Object.entries(this._effect.defaults()))
      if (state[key] != value)
        return true
    return false
  }
}


class AutoSkip {

  constructor(effect) {
    this._effect = effect
    this.input = this._effect.input
    this.output = this._effect.output
    this._last = this._effect.defaults()
  }

  defaults() {
    return this._effect.defaults()
  }

  call(pulse, state) {
    state = Object.fromEntries(Object.keys(this._last).map(key => [key, state[key]]))
    if (jsonEqual(Object.entries(state), Object.entries(this._last)))
      return
    this._last = state
    this._effect.call(pulse, state)
  }

  close() {
    this._effect.close()
  }
}


class Volume {

  constructor() {
    this.input = new tone.Gain(1.0)
    this.output = this.input
  }

  defaults() {
    return {'vol': 1.0}
  }

  call(pulse, state) {
    this.input.gain.setValueAtTime(state['vol'], pulse)
  }

  close() {
    this.input.dispose()
  }
}


class Compressor {

  constructor() {
    this.input = new tone.Compressor(0, 20)
    this.output = this.input
  }

  defaults() {
    return {'cpr': 0.0}
  }

  call(pulse, state) {
    this.input.threshold.setValueAtTime(state['cpr'], pulse)
  }

  close() {
    this.input.dispose()
  }
}


class Panner {

  constructor() {
    this.output = new tone.Panner()
    this.input = this.output
  }

  defaults() {
    return {'pan': 0}
  }

  call(pulse, state) {
    this.input.pan.setValueAtTime(state['pan'], pulse)
  }

  close() {
    this.input.dispose()
  }
}


class Filter {

  constructor() {
    this.input = new tone.Filter(0, 'highpass', -48)
    this.output = new tone.Filter(20000, 'lowpass', -48)
    this.input.connect(this.output)
  }

  defaults() {
    return {'hpf': 0, 'lpf': 20000}
  }

  call(pulse, state) {
    this.input.frequency.setValueAtTime(state['hpf'], pulse)
    this.output.frequency.setValueAtTime(state['lpf'], pulse)
  }

  close() {
    this.input.dispose()
    this.output.dispose()
  }
}


class Distortion {

  constructor() {
    this.output = new tone.Distortion()
    this.input = this.output
  }

  defaults() {
    return {'dis': 0}
  }

  call(pulse, state) {
    this.input.distortion = state['dis']
  }

  close() {
    this.input.dispose()
  }
}


class Reverb {

  constructor() {
    this.output = new tone.Freeverb(0)
    this.input = this.output
  }

  defaults() {
    return {'rev': 0}
  }

  call(pulse, state) {
    this.input.roomSize.setValueAtTime(state['rev'], pulse)
  }

  close() {
    this.input.dispose()
  }
}


class Delay {

  constructor() {
    this.input = new tone.Gain(1)
    this.output = new tone.Gain(1)
    this._delay = new tone.Delay(0.0)
    this._gain = new tone.Gain(0.2)
    this.input.chain(this._delay, this._gain, this.output)
    this.input.connect(this.output)
  }

  defaults() {
    return {'dly': 0.0}
  }

  call(pulse, state) {
    this._delay.delayTime.setValueAtTime(state['dly'])
    this._gain.gain.setValueAtTime(state['dly'] && 0.5)
  }

  close() {
    this.input.dispose()
    this.output.dispose()
    this._delay.dispose()
    this._gain.dispose()
  }
}


class Equalizer {

  constructor() {
    this.output = new tone.EQ3(0, 0, 0)
    this.input = this.output
  }

  defaults() {
    return {'low': 0.0, 'mid': 0.0, 'hig': 0.0}
  }

  call(pulse, state) {
    this.output.low.setValueAtTime(state['low'], pulse)
    this.output.mid.setValueAtTime(state['mid'], pulse)
    this.output.high.setValueAtTime(state['hig'], pulse)
  }

  close() {
    this.input.dispose()
  }
}


window.Engine = Engine
