/** NEW implementation, not recovery of the lost module. Read-only Unicode diagnostics.
 * Experience §5 requires exact text return and honest font coverage; user-defined
 * UI languages and content-language scope are distinct. No detection/translation. */
export const CONTENT_LANGUAGE_VERSION='review-content-language/1';
export const UI_LANGUAGES=Object.freeze(['zh','en','ko']);
export const CONTENT_LANGUAGES=Object.freeze(['zh','en','ko','ja','fr','de','es','pt','ru','ar','hi','id']);
export const CONTENT_TEXT_LIMIT=1000000;
function validText(text){
 if(typeof text!=='string')throw Error('INVALID_CONTENT_TEXT');
 if(text.length>CONTENT_TEXT_LIMIT)throw Error('CONTENT_TEXT_LIMIT');
 for(let i=0;i<text.length;i++){
  const unit=text.charCodeAt(i);
  if(unit>=0xd800&&unit<=0xdbff){const next=text.charCodeAt(++i);if(!(next>=0xdc00&&next<=0xdfff))throw Error('INVALID_UNICODE_SURROGATE')}
  else if(unit>=0xdc00&&unit<=0xdfff)throw Error('INVALID_UNICODE_SURROGATE');
 }
 return text;
}
function segments(text,Segmenter){
 if(typeof Segmenter!=='function')return null;
 try{return new Segmenter(undefined,{granularity:'grapheme'}).segment(text)}catch{return null}
}
export function contentDiagnostics(text,{Segmenter=globalThis.Intl?.Segmenter}={}){
 validText(text);const units=segments(text,Segmenter);let graphemes=null;
 if(units){graphemes=0;for(const _ of units)graphemes++}
 const bidiControls=[...text.matchAll(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu)].map(m=>({utf16Offset:m.index,codePoint:'U+'+m[0].codePointAt(0).toString(16).toUpperCase().padStart(4,'0')}));
 const escapedForInspection=text.replace(/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/gu,c=>'[U+'+c.codePointAt(0).toString(16).toUpperCase().padStart(4,'0')+']');
 return{original:text,escapedForInspection,utf16Units:text.length,codePoints:[...text].length,graphemes,segmentation:units?'INTL_SEGMENTER':'UNAVAILABLE',bidiControls,directionHint:/[\u0590-\u08ff\ufb1d-\ufdff\ufe70-\ufefc]/u.test(text)?'RTL_SCRIPT_PRESENT':'AUTO',displayIsolation:'USE_DIR_AUTO_AND_UNICODE_BIDI_ISOLATE',fontCoverage:'UNKNOWN',languageUnderstanding:'NOT_TESTED',transformed:false};
}
/** Optional display-only excerpt; never use it as a filename or stored source.
 * If grapheme segmentation is unavailable, preserve the whole text rather than
 * pretending code-point slicing preserves an emoji/combining sequence. */
export function contentExcerpt(text,maxGraphemes,{Segmenter=globalThis.Intl?.Segmenter}={}){
 validText(text);if(!Number.isSafeInteger(maxGraphemes)||maxGraphemes<0||maxGraphemes>CONTENT_TEXT_LIMIT)throw Error('INVALID_GRAPHEME_LIMIT');
 const units=segments(text,Segmenter);if(!units)return{text,original:text,truncated:false,segmentation:'UNAVAILABLE'};
 let end=0,count=0,truncated=false;
 for(const unit of units){if(count===maxGraphemes){truncated=true;break}end=unit.index+unit.segment.length;count++}
 return{text:truncated?text.slice(0,end):text,original:text,truncated,segmentation:'INTL_SEGMENTER'};
}

/** Browser selection offsets are UTF-16; SavedWork range edits use Python code points.
 * Reject split graphemes instead of silently changing the user's selected text.
 * Without segmentation callers must use explicit whole-field replacement. */
export function createContentSelectionIndex(text,{Segmenter=globalThis.Intl?.Segmenter}={}){
 validText(text);const units=segments(text,Segmenter);if(!units)throw Error('GRAPHEME_SEGMENTATION_UNAVAILABLE');
 const boundaries=new Set([0,text.length]);for(const unit of units)boundaries.add(unit.index);
 const codepointOffsets=[0],codepointsAt=new Map([[0,0]]);let offset=0,count=0;for(const point of text){offset+=point.length;codepointOffsets.push(offset);codepointsAt.set(offset,++count)}
 function range(start,end){if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start<0||end<start||end>text.length)throw Error('INVALID_SELECTION_RANGE');if(!boundaries.has(start)||!boundaries.has(end))throw Error('SELECTION_SPLITS_GRAPHEME');return Object.freeze({start:codepointsAt.get(start),end:codepointsAt.get(end),expected:text.slice(start,end),offset_unit:'unicode_codepoint'})}
 return Object.freeze({range,fromCodePoints(start,end){if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start<0||end<start||end>=codepointOffsets.length)throw Error('INVALID_SELECTION_RANGE');return range(codepointOffsets[start],codepointOffsets[end])}});
}
export function contentSelectionRange(text,start,end,options={}){return createContentSelectionIndex(text,options).range(start,end)}
