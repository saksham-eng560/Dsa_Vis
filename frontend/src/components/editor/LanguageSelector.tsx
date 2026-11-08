/** Language dropdown with an "Auto" option that shows the detected language. */
import type { Language, LanguageChoice } from '../../types';
import { LANGUAGE_LABELS } from '../../utils/codeDetection';

interface LanguageSelectorProps {
  value: LanguageChoice;
  detected: Language;
  onChange: (value: LanguageChoice) => void;
}

export function LanguageSelector({ value, detected, onChange }: LanguageSelectorProps) {
  return (
    <label className="flex items-center">
      <span className="sr-only">Language</span>
      <select
        className="field cursor-pointer"
        value={value}
        onChange={(e) => onChange(e.target.value as LanguageChoice)}
        aria-label="Programming language"
      >
        <option value="auto">Auto · {LANGUAGE_LABELS[detected]}</option>
        {(Object.keys(LANGUAGE_LABELS) as Language[]).map((lang) => (
          <option key={lang} value={lang}>
            {LANGUAGE_LABELS[lang]}
          </option>
        ))}
      </select>
    </label>
  );
}
