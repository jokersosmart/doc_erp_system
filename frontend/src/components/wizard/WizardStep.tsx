/**
 * WizardStep — renders one wizard question per step (T035).
 * Supports: text, select, multiselect input types.
 * Labels are locale-aware via react-i18next locale context.
 */
import { useTranslation } from 'react-i18next';

export interface StepOption {
  value: string | number;
  label_zh: string;
  label_en: string;
}

export interface WizardQuestion {
  step: number;
  key: string;
  type: 'text' | 'select' | 'multiselect';
  label_zh: string;
  label_en: string;
  placeholder_zh?: string;
  placeholder_en?: string;
  options?: StepOption[];
  required: boolean;
  depends_on?: { key: string; not_value: string };
}

interface WizardStepProps {
  question: WizardQuestion;
  value: string | string[] | number | null;
  onChange: (key: string, value: string | string[] | number | null) => void;
}

export function WizardStep({ question, value, onChange }: WizardStepProps) {
  const { i18n } = useTranslation();
  const isZh = i18n.language.startsWith('zh');

  const label = isZh ? question.label_zh : question.label_en;
  const placeholder = isZh ? question.placeholder_zh : question.placeholder_en;

  const optionLabel = (opt: StepOption) => (isZh ? opt.label_zh : opt.label_en);

  if (question.type === 'text') {
    return (
      <div className="wizard-step">
        <label className="wizard-step__label">
          {label}
          {question.required && <span className="wizard-step__required"> *</span>}
        </label>
        <input
          type="text"
          className="wizard-step__input"
          placeholder={placeholder}
          value={(value as string) ?? ''}
          onChange={(e) => onChange(question.key, e.target.value)}
        />
      </div>
    );
  }

  if (question.type === 'select') {
    return (
      <div className="wizard-step">
        <label className="wizard-step__label">
          {label}
          {question.required && <span className="wizard-step__required"> *</span>}
        </label>
        <select
          className="wizard-step__select"
          value={(value as string | number) ?? ''}
          onChange={(e) => {
            const raw = e.target.value;
            const parsed = !isNaN(Number(raw)) && raw !== '' ? Number(raw) : raw;
            onChange(question.key, parsed);
          }}
        >
          <option value="">— {isZh ? '請選擇' : 'Select'} —</option>
          {question.options?.map((opt) => (
            <option key={String(opt.value)} value={String(opt.value)}>
              {optionLabel(opt)}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (question.type === 'multiselect') {
    const selected = (value as string[]) ?? [];
    const toggle = (v: string) => {
      if (selected.includes(v)) {
        onChange(question.key, selected.filter((x) => x !== v));
      } else {
        onChange(question.key, [...selected, v]);
      }
    };

    return (
      <div className="wizard-step">
        <label className="wizard-step__label">
          {label}
          {question.required && <span className="wizard-step__required"> *</span>}
        </label>
        <div className="wizard-step__checkgroup">
          {question.options?.map((opt) => (
            <label key={String(opt.value)} className="wizard-step__check-item">
              <input
                type="checkbox"
                checked={selected.includes(String(opt.value))}
                onChange={() => toggle(String(opt.value))}
              />
              <span>{optionLabel(opt)}</span>
            </label>
          ))}
        </div>
      </div>
    );
  }

  return null;
}
