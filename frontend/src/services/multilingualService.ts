// src/services/multilingualService.ts

export interface LanguageOption {
  code: string;
  name: string;
  nativeName: string;
  flag: string;
  available: boolean;
}

class MultilingualService {
  private currentLanguage: string = 'en';
  private readonly supportedLanguages: LanguageOption[] = [
    { code: 'en', name: 'English', nativeName: 'English', flag: '🇺🇸', available: true },
    { code: 'es', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸', available: true },
    { code: 'fr', name: 'French', nativeName: 'Français', flag: '🇫🇷', available: true },
    { code: 'pt', name: 'Portuguese', nativeName: 'Português', flag: '🇧🇷', available: true },
  ];

  constructor() {
    this.loadStoredLanguage();
  }

  private loadStoredLanguage(): void {
    try {
      const stored = localStorage.getItem('askimmigrate_ui_language');
      if (stored && this.isLanguageSupported(stored)) {
        this.currentLanguage = stored;
      } else {
        // Detect from browser
        this.currentLanguage = this.detectBrowserLanguage();
      }
    } catch (error) {
      console.warn('Failed to load stored language:', error);
      this.currentLanguage = 'en';
    }
  }

  private detectBrowserLanguage(): string {
    const browserLang = navigator.language.toLowerCase();
    
    if (browserLang.startsWith('es')) return 'es';
    if (browserLang.startsWith('fr')) return 'fr';
    if (browserLang.startsWith('pt')) return 'pt';
    
    return 'en'; // Default fallback
  }

  getCurrentLanguage(): string {
    return this.currentLanguage;
  }

  setLanguage(languageCode: string): void {
    if (this.isLanguageSupported(languageCode)) {
      this.currentLanguage = languageCode;
      try {
        localStorage.setItem('askimmigrate_ui_language', languageCode);
      } catch (error) {
        console.warn('Failed to save language preference:', error);
      }
    }
  }

  getAvailableLanguages(): LanguageOption[] {
    return [...this.supportedLanguages]; // Return copy
  }

  isLanguageSupported(languageCode: string): boolean {
    return this.supportedLanguages.some(lang => lang.code === languageCode);
  }

  getCurrentLanguageInfo(): LanguageOption | null {
    return this.supportedLanguages.find(lang => lang.code === this.currentLanguage) || null;
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
        selectLanguage: 'Interface Language',
        questionLanguageNote: 'Ask questions in any language - responses will match your question language!',
        uiLanguageNote: 'Use the language selector above to change the interface language.',
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
        selectLanguage: 'Idioma de Interfaz',
        questionLanguageNote: '¡Haga preguntas en cualquier idioma - las respuestas coincidirán con el idioma de su pregunta!',
        uiLanguageNote: 'Use el selector de idioma arriba para cambiar el idioma de la interfaz.',
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
        selectLanguage: 'Langue d\'Interface',
        questionLanguageNote: 'Posez des questions dans n\'importe quelle langue - les réponses correspondront à la langue de votre question!',
        uiLanguageNote: 'Utilisez le sélecteur de langue ci-dessus pour changer la langue de l\'interface.',
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
        selectLanguage: 'Idioma da Interface',
        questionLanguageNote: 'Faça perguntas em qualquer idioma - as respostas corresponderão ao idioma da sua pergunta!',
        uiLanguageNote: 'Use o seletor de idioma acima para alterar o idioma da interface.',
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
const multilingualService = new MultilingualService();

export default multilingualService;