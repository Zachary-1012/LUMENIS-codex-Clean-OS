/** Review-only file preparation preference. Never changes a prepared manifest. */
export const FILE_CHUNK_OPTIONS=Object.freeze([65536,262144,1048576]);
export const filePreferenceDefaults=Object.freeze({chunkBytes:262144});
export function filePreferences(value){return{chunkBytes:FILE_CHUNK_OPTIONS.includes(value?.chunkBytes)?value.chunkBytes:filePreferenceDefaults.chunkBytes}}
