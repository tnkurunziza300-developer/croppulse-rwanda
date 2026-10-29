import type { FormEvent } from 'react';
import { X } from 'lucide-react';

interface FarmProfileFormProps {
  name: string;
  district: string;
  area: string;
  districts: readonly string[];
  busy: boolean;
  onNameChange: (value: string) => void;
  onDistrictChange: (value: string) => void;
  onAreaChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onClose: () => void;
}

export function FarmProfileForm({
  name,
  district,
  area,
  districts,
  busy,
  onNameChange,
  onDistrictChange,
  onAreaChange,
  onSubmit,
  onClose,
}: FarmProfileFormProps) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <div className="panel-heading">
        <div>
          <h2>New farm profile</h2>
          <p>Only you can access this account’s farm records.</p>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close form">
          <X size={18} />
        </button>
      </div>
      <div className="form-grid">
        <label>
          Farm name
          <input value={name} onChange={(event) => onNameChange(event.target.value)} required maxLength={120} />
        </label>
        <label>
          District
          <select value={district} onChange={(event) => onDistrictChange(event.target.value)}>
            {districts.map((item) => <option key={item}>{item}</option>)}
          </select>
        </label>
        <label>
          Area (hectares)
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={area}
            onChange={(event) => onAreaChange(event.target.value)}
            placeholder="Optional"
          />
        </label>
        <div className="form-end">
          <button className="button button-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save farm'}
          </button>
        </div>
      </div>
    </form>
  );
}
