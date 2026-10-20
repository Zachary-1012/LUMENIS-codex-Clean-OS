// Independent listening fixture. Chapter times are supplied, never inferred by ASR.
const clone = value => structuredClone(value);
const validName = name => typeof name === 'string' && name.trim().length > 0 && name.trim().length <= 80;

export function validateChapterSource(source) {
  if (!source || typeof source.id !== 'string' || !source.id.trim() ||
      typeof source.version !== 'string' || !source.version.trim() ||
      !Number.isInteger(source.sampleRate) || source.sampleRate < 8000 || source.sampleRate > 48000 ||
      !Number.isSafeInteger(source.sampleCount) || source.sampleCount < 1 || source.sampleCount > 480000) {
    throw Error('无效的测试音版本或采样信息');
  }
  return {...source};
}

export function validateChapters(chapters, source) {
  validateChapterSource(source);
  if (!Array.isArray(chapters) || chapters.length > 100) throw Error('章节列表无效');
  const ids = new Set();
  let previous = -1;
  for (const chapter of chapters) {
    if (!chapter || typeof chapter.id !== 'string' || !chapter.id.trim() || ids.has(chapter.id) ||
        !validName(chapter.name) || !Number.isSafeInteger(chapter.start) ||
        chapter.start < 0 || chapter.start >= source.sampleCount || chapter.start <= previous) {
      throw Error('章节须有名称、唯一标识，且起点在音频范围内严格递增');
    }
    ids.add(chapter.id);
    previous = chapter.start;
  }
  return chapters.map(chapter => ({id: chapter.id, name: chapter.name.trim(), start: chapter.start}));
}

export function initialChapters(source, chapters = []) {
  return {
    source: validateChapterSource(source), chapters: validateChapters(chapters, source),
    revision: 1, selected: chapters[0]?.id ?? null, proposal: null, history: [],
    loop: null, session: 1, notice: '人工章节已就绪；选择章节可定位，不自动播放。'
  };
}

export function chapterRange(state, id = state.selected) {
  const index = state.chapters.findIndex(chapter => chapter.id === id);
  if (index < 0) return null;
  return {start: state.chapters[index].start, end: state.chapters[index + 1]?.start ?? state.source.sampleCount};
}

export function chapterSeekSample(state, id = state.selected) {
  return chapterRange(state, id)?.start ?? null;
}

export function chapterStartFromSeconds(seconds, source) {
  validateChapterSource(source);
  if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds < 0 || seconds >= source.sampleCount / source.sampleRate) {
    throw Error('章节起点须在音频范围内');
  }
  const sample = Math.round(seconds * source.sampleRate);
  if (sample >= source.sampleCount) throw Error('章节起点不能落在音频终点');
  return sample;
}

export function chapterAudioSamples(samples, state, id = state.selected) {
  const range = chapterRange(state, id);
  if (!(samples instanceof Float32Array) || samples.length !== state.source.sampleCount || !range) {
    throw Error('当前章节与音频采样不匹配');
  }
  for (const sample of samples) if (!Number.isFinite(sample)) throw Error('音频包含无效采样');
  return samples.slice(range.start, range.end);
}

function stopSession(state) {
  state.loop = null;
  state.session++;
}

function saveEdit(state, chapters, notice) {
  state.history.push({chapters: clone(state.chapters), selected: state.selected});
  if (state.history.length > 30) state.history.shift();
  state.chapters = chapters;
  state.revision++;
  state.proposal = null;
  stopSession(state);
  state.notice = notice;
  return state;
}

export function chaptersReduce(state, event) {
  const next = clone(state);
  const selected = next.chapters.find(chapter => chapter.id === (event.id ?? next.selected));
  switch (event.type) {
    case 'select-source': {
      try {
        const replacement = initialChapters(event.source, event.chapters);
        return {...replacement, session: next.session + 1, notice: '已切换测试音版本；旧播放和待修订均已停止。'};
      } catch (error) {
        stopSession(next);
        next.notice = error.message + '；保留上一份可用素材，未继续播放。';
        return next;
      }
    }
    case 'select':
      if (!selected) return {...next, notice: '找不到此章节；保留当前选择。'};
      next.selected = selected.id;
      next.proposal = null;
      stopSession(next);
      next.notice = '已选择章节；精确定位到起点采样，不自动播放。';
      return next;
    case 'propose-edit': {
      if (!selected) return {...next, proposal: null, notice: '请先选择有效章节。'};
      try {
        const chapters = next.chapters.map(chapter => chapter.id === selected.id
          ? {...chapter, name: event.name, start: event.start} : chapter);
        chapters.sort((a, b) => a.start - b.start);
        const candidate = validateChapters(chapters, next.source);
        next.proposal = {
          id: selected.id, base: next.revision, sourceId: next.source.id,
          sourceVersion: next.source.version, chapters: candidate
        };
        next.notice = '待应用：章节按新起点排序；测试音采样不会被重排或剪切。';
      } catch (error) {
        next.proposal = null;
        next.notice = error.message + '；当前章节未改变。';
      }
      return next;
    }
    case 'apply-edit': {
      const proposal = next.proposal;
      if (!proposal) return {...next, notice: '没有待应用的章节修订。'};
      if (proposal.base !== next.revision || proposal.sourceId !== next.source.id || proposal.sourceVersion !== next.source.version) {
        return {...next, proposal: null, notice: '素材或章节版本已变化；请重新预览修订。'};
      }
      try {
        const candidate = validateChapters(proposal.chapters, next.source);
        if (candidate.length !== next.chapters.length || candidate.some(chapter => !next.chapters.some(old => old.id === chapter.id))) {
          throw Error('章节集合已变化');
        }
        if (JSON.stringify(candidate) === JSON.stringify(next.chapters)) {
          return {...next, proposal: null, notice: '章节没有变化；未创建新修订。'};
        }
        return saveEdit(next, candidate, '已更新本地章节并按起点排序；音频未改动，旧试听已停止。');
      } catch (error) {
        return {...next, proposal: null, notice: error.message + '；保留原章节。'};
      }
    }
    case 'cancel-edit':
      return {...next, proposal: null, notice: '已取消待修订；原章节和音频保留。'};
    case 'undo': {
      const previous = next.history.pop();
      if (!previous) return {...next, notice: '没有可撤销的章节修订。'};
      next.chapters = previous.chapters;
      next.selected = previous.selected;
      next.revision++;
      next.proposal = null;
      stopSession(next);
      next.notice = '已撤销上次章节修订；名称、顺序、起点已还原，音频未变。';
      return next;
    }
    case 'start-loop': {
      if (!selected) return {...next, notice: '请先选择有效章节。'};
      const range = chapterRange(next, selected.id);
      next.selected = selected.id;
      next.session++;
      next.loop = {
        id: selected.id, ...range, session: next.session, revision: next.revision,
        sourceId: next.source.id, sourceVersion: next.source.version
      };
      next.notice = '循环区间已准备；等待实际播放器开始。';
      return next;
    }
    case 'stop':
    case 'media-error':
      stopSession(next);
      next.notice = event.type === 'media-error' ? '测试音无法播放；章节修订仍保留。' : '已停止试听与循环。';
      return next;
    default:
      return next;
  }
}

export function chapterSessionIsCurrent(state, session) {
  return Number.isSafeInteger(session) && session === state.session;
}

export function activeChapterLoop(state) {
  const loop = state.loop;
  if (!loop || loop.session !== state.session || loop.revision !== state.revision ||
      loop.sourceId !== state.source.id || loop.sourceVersion !== state.source.version) return null;
  const range = chapterRange(state, loop.id);
  if (!range || range.start !== loop.start || range.end !== loop.end) return null;
  return {...loop};
}
