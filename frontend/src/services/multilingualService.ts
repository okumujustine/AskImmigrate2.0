export interface LanguageOption {
  code: string;
  name: string;
  nativeName: string;
  flag: string;
  available: boolean;
}

export interface DetectionResult {
  language: string;
  confidence: number;
  supported: boolean;
  detection_method: string;
}

export interface MultilingualCapabilities {
  supported_languages: Array<{
    code: string;
    name: string;
    native_name: string;
    native_llm: boolean;
    translation_available: boolean;
    quality: string;
  }>;
  multilingual_enabled: boolean;
  service_status: string;
}

class MultilingualService {
  private apiUrl: string;
  private currentLanguage: string = 'en';
  private supportedLanguages: LanguageOption[] = [
    { code: 'en', name: 'English', nativeName: 'English', flag: '🇺🇸', available: true },
    { code: 'es', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸', available: true },
    { code: 'fr', name: 'French', nativeName: 'Français', flag: '🇫🇷', available: true },
    { code: 'pt', name: 'Portuguese', nativeName: 'Português', flag: '🇧🇷', available: true },
  ];

  constructor(apiUrl: string) {
    this.apiUrl = apiUrl;
    this.loadStoredLanguage();
    this.initializeCapabilities();
  }

  private loadStoredLanguage(): void {
    try {
      const stored = localStorage.getItem('askimmigrate_language');
      if (stored) {
        this.currentLanguage = stored;
      } else {
        // Try to detect from browser
        this.currentLanguage = this.detectBrowserLanguage();
      }
    } catch (error) {
      console.warn('Failed to load stored language:', error);
    }
  }

  private detectBrowserLanguage(): string {
    const browserLang = navigator.language.toLowerCase();
    
    if (browserLang.startsWith('es')) return 'es';
    if (browserLang.startsWith('fr')) return 'fr';
    if (browserLang.startsWith('pt')) return 'pt';
    
    return 'en'; // Default fallback
  }

  private async initializeCapabilities(): Promise<void> {
    try {
      const response = await fetch(`${this.apiUrl}/api/languages/supported`);
      if (response.ok) {
        const capabilities: MultilingualCapabilities = await response.json();
        console.log('Multilingual capabilities loaded:', capabilities);
      }
    } catch (error) {
      console.warn('Failed to load multilingual capabilities, using defaults:', error);
    }
    
    // Always make basic languages available for UI
    this.supportedLanguages = this.supportedLanguages.map(lang => ({
      ...lang,
      available: true // Always available for UI language switching
    }));
  }

  getCurrentLanguage(): string {
    return this.currentLanguage;
  }

  setLanguage(languageCode: string): void {
    if (this.isLanguageSupported(languageCode)) {
      this.currentLanguage = languageCode;
      localStorage.setItem('askimmigrate_language', languageCode);
    }
  }

  getSupportedLanguages(): LanguageOption[] {
    return this.supportedLanguages;
  }

  getAvailableLanguages(): LanguageOption[] {
    return this.supportedLanguages.filter(lang => lang.available);
  }

  isLanguageSupported(languageCode: string): boolean {
    return this.supportedLanguages.some(lang => lang.code === languageCode && lang.available);
  }

  getCurrentLanguageInfo(): LanguageOption | null {
    return this.supportedLanguages.find(lang => lang.code === this.currentLanguage) || null;
  }

  async detectLanguage(text: string): Promise<DetectionResult> {
    try {
      const response = await fetch(`${this.apiUrl}/api/detect-language`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });

      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.warn('Language detection failed:', error);
    }

    // Client-side fallback detection
    return this.clientSideLanguageDetection(text);
  }

  private clientSideLanguageDetection(text: string): DetectionResult {
    const textLower = text.toLowerCase();
    
    // Spanish patterns
    const spanishPatterns = ['¿', '¡', 'ñ', 'inmigración', 'visa', 'cómo', 'qué', 'cuándo'];
    const spanishScore = spanishPatterns.filter(pattern => textLower.includes(pattern)).length;
    
    if (spanishScore > 0) {
      return {
        language: 'es',
        confidence: Math.min(0.3 + (spanishScore * 0.15), 0.9),
        supported: true,
        detection_method: 'client_pattern'
      };
    }

    // French patterns
    if (textLower.includes('français') || textLower.includes('où') || textLower.includes('ç')) {
      return {
        language: 'fr',
        confidence: 0.6,
        supported: this.isLanguageSupported('fr'),
        detection_method: 'client_pattern'
      };
    }

    // Portuguese patterns
    if (textLower.includes('português') || textLower.includes('ção') || textLower.includes('imigração')) {
      return {
        language: 'pt',
        confidence: 0.6,
        supported: this.isLanguageSupported('pt'),
        detection_method: 'client_pattern'
      };
    }

    // Default to English
    return {
      language: 'en',
      confidence: 0.8,
      supported: true,
      detection_method: 'client_fallback'
    };
  }

  // Get localized UI strings
  getUIStrings(languageCode?: string): Record<string, string> {
    const lang = languageCode || this.currentLanguage;
    
    const strings: Record<string, Record<string, string>> = {
      en: {
        newChat: 'New Chat',
        askImmigrate: 'AskImmigrate',
        welcome: 'Welcome to AskImmigrate',
        welcomeDescription: 'Ask any question about immigration and get detailed answers.',
        exampleQuestions: 'Example questions:',
        continueChatPlaceholder: 'Continue the conversation...',
        newChatPlaceholder: 'Ask a question about immigration to start a new conversation...',
        thinking: 'Thinking...',
        sessionReady: 'Ready to chat',
        sessionActive: 'Session:',
        errorSending: 'Failed to send message. Please try again.',
        errorLoading: 'Failed to load chat sessions',
        errorCreating: 'Failed to create new chat',
        selectLanguage: 'Interface Language',
        autoDetect: 'Auto-detect',
        languageChanged: 'Language changed to',
      },
      es: {
        newChat: 'Nueva Conversación',
        askImmigrate: 'AskImmigrate',
        welcome: 'Bienvenido a AskImmigrate',
        welcomeDescription: 'Haga cualquier pregunta sobre inmigración y obtenga respuestas detalladas.',
        exampleQuestions: 'Preguntas de ejemplo:',
        continueChatPlaceholder: 'Continúe la conversación...',
        newChatPlaceholder: 'Haga una pregunta sobre inmigración para comenzar una nueva conversación...',
        thinking: 'Pensando...',
        sessionReady: 'Listo para conversar',
        sessionActive: 'Sesión:',
        errorSending: 'Error al enviar mensaje. Por favor, inténtelo de nuevo.',
        errorLoading: 'Error al cargar sesiones de chat',
        errorCreating: 'Error al crear nueva conversación',
        selectLanguage: 'Idioma de Interfaz',
        autoDetect: 'Detección automática',
        languageChanged: 'Idioma cambiado a',
      },
      fr: {
        newChat: 'Nouvelle Conversation',
        askImmigrate: 'AskImmigrate',
        welcome: 'Bienvenue sur AskImmigrate',
        welcomeDescription: 'Posez toute question sur l\'immigration et obtenez des réponses détaillées.',
        exampleQuestions: 'Exemples de questions:',
        continueChatPlaceholder: 'Continuez la conversation...',
        newChatPlaceholder: 'Posez une question sur l\'immigration pour commencer une nouvelle conversation...',
        thinking: 'Réflexion...',
        sessionReady: 'Prêt à discuter',
        sessionActive: 'Session:',
        errorSending: 'Échec de l\'envoi du message. Veuillez réessayer.',
        errorLoading: 'Échec du chargement des sessions de chat',
        errorCreating: 'Échec de la création d\'une nouvelle conversation',
        selectLanguage: 'Langue d\'Interface',
        autoDetect: 'Détection automatique',
        languageChanged: 'Langue changée en',
      },
      pt: {
        newChat: 'Nova Conversa',
        askImmigrate: 'AskImmigrate',
        welcome: 'Bem-vindo ao AskImmigrate',
        welcomeDescription: 'Faça qualquer pergunta sobre imigração e obtenha respostas detalhadas.',
        exampleQuestions: 'Perguntas de exemplo:',
        continueChatPlaceholder: 'Continue a conversa...',
        newChatPlaceholder: 'Faça uma pergunta sobre imigração para iniciar uma nova conversa...',
        thinking: 'Pensando...',
        sessionReady: 'Pronto para conversar',
        sessionActive: 'Sessão:',
        errorSending: 'Falha ao enviar mensagem. Tente novamente.',
        errorLoading: 'Falha ao carregar sessões de chat',
        errorCreating: 'Falha ao criar nova conversa',
        selectLanguage: 'Idioma da Interface',
        autoDetect: 'Detecção automática',
        languageChanged: 'Idioma alterado para',
      }
    };

    return strings[lang] || strings.en;
  }

  // Get localized example questions
  getExampleQuestions(languageCode?: string): string[] {
    const lang = languageCode || this.currentLanguage;
    
    const examples: Record<string, string[]> = {
      en: [
        '"What is an F1 visa?"',
        '"How to apply for a Green Card?"',
        '"What documents do I need for H1B?"'
      ],
      es: [
        '"¿Qué es una visa F1?"',
        '"¿Cómo solicitar una Tarjeta Verde?"',
        '"¿Qué documentos necesito para H1B?"'
      ],
      fr: [
        '"Qu\'est-ce qu\'un visa F1?"',
        '"Comment demander une Carte Verte?"',
        '"Quels documents ai-je besoin pour H1B?"'
      ],
      pt: [
        '"O que é um visto F1?"',
        '"Como solicitar um Green Card?"',
        '"Quais documentos preciso para H1B?"'
      ]
    };

    return examples[lang] || examples.en;
  }
}

// Create singleton instance
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8088';
export const multilingualService = new MultilingualService(API_BASE_URL);

export default multilingualService;