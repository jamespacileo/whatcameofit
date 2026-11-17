// An id for each score chip's panel. A page draws many chips, in lists whose rows have no
// id of their own, so the ids are counted: unique on a page, and nothing reads them.
let count = 0;

export function nextScoreId(): string {
  count += 1;
  return `score-${count}`;
}
