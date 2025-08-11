// src/components/LanguageSelector.tsx

import { ChevronDown, Globe } from "lucide-react";
import React, { useState, useRef, useEffect } from "react";
import multilingualService, {
  type LanguageOption,
} from "../services/multilingualService";

interface LanguageSelectorProps {
  currentLanguage: string;
  onLanguageChange: (languageCode: string) => void;
  className?: string;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  currentLanguage,
  onLanguageChange,
  className = "",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [availableLanguages] = useState<LanguageOption[]>(() =>
    multilingualService.getAvailableLanguages()
  );
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLanguageSelect = (languageCode: string) => {
    onLanguageChange(languageCode);
    setIsOpen(false);
  };

  const currentLangInfo = availableLanguages.find(
    (lang) => lang.code === currentLanguage
  );
  const uiStrings = multilingualService.getUIStrings(currentLanguage);

  if (availableLanguages.length <= 1) {
    return null; // Don't show selector if only one language is available
  }

  return (
    <div className={`language-selector ${className}`} ref={dropdownRef}>
      <button
        className="language-selector-button"
        onClick={() => setIsOpen(!isOpen)}
        type="button"
        title="Change interface language"
      >
        <Globe size={16} />
        <span className="language-text">
          {currentLangInfo?.flag} {currentLangInfo?.nativeName || "English"}
        </span>
        <ChevronDown size={14} className={`chevron ${isOpen ? "open" : ""}`} />
      </button>

      {isOpen && (
        <div className="language-dropdown">
          <div className="language-dropdown-header">
            <Globe size={14} />
            <span>{uiStrings.selectLanguage}</span>
          </div>

          {availableLanguages.map((language) => (
            <button
              key={language.code}
              className={`language-option ${
                language.code === currentLanguage ? "active" : ""
              }`}
              onClick={() => handleLanguageSelect(language.code)}
              type="button"
            >
              <span className="language-flag">{language.flag}</span>
              <div className="language-info">
                <span className="language-native">{language.nativeName}</span>
                <span className="language-english">{language.name}</span>
              </div>
              {language.code === currentLanguage && (
                <div className="language-check">✓</div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
