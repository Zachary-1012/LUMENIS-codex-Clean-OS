/** View-only route semantics; never changes hash, task state or modal ownership. */
export function markCurrentRoute(links,current){for(const link of links){const active=link.dataset.id===current;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current')}}
export function focusCurrentWork(work,dialogs=[]){if(!work||Array.from(dialogs).some(d=>d.open))return false;work.focus();return true}
