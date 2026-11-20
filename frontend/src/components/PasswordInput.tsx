import React, { useState } from "react";

interface PasswordInputProps {
  id: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  required?: boolean;
  minLength?: number;
  placeholder?: string;
}

export const PasswordInput: React.FC<PasswordInputProps> = ({
  id,
  value,
  onChange,
  required,
  minLength,
  placeholder,
}) => {
  const [visible, setVisible] = useState(false);

  return (
    <div className="password-wrapper">
      <input
        id={id}
        type={visible ? "text" : "password"}
        className="form-input password-input"
        required={required}
        minLength={minLength}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
      />
      <button
        type="button"
        className="password-toggle-btn"
        onClick={() => setVisible((prev) => !prev)}
        aria-label={visible ? "Hide password" : "Show password"}
      >
        {visible ? "🙈 Hide" : "👁️ Show"}
      </button>
    </div>
  );
};