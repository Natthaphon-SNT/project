const EMOJI_PATTERN = /[\u{1F000}-\u{1FAFF}\u2300-\u23FF\u2600-\u27BF\u20E3\uFE0F\u200D]/gu;

export function stripEmojiText(text: string): string {
  return text.replace(EMOJI_PATTERN, '');
}

export function stripEmojiDeep<T>(value: T): T {
  if (typeof value === 'string') return stripEmojiText(value) as T;
  if (Array.isArray(value)) return value.map(stripEmojiDeep) as T;
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, stripEmojiDeep(item)])
    ) as T;
  }
  return value;
}
