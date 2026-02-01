/* Generated from design-system-tokens.json. Do not edit directly. */

export const tokens = {
  color: {
    brand: {
      orange500: '#FD5108',
      orange300: '#FFAA72',
      orange100: '#FFE8D4',
      gradientPrimary: 'linear-gradient(135deg, #FD5108, #FE7C39)',
    },
    neutral: {
      black: '#000000',
      white: '#FFFFFF',
      grey500: '#A1A8B3',
      grey400: '#B5BCC4',
      grey300: '#CBD1D6',
      grey200: '#DFE3E6',
      grey100: '#EEEFF1',
    },
    text: {
      primary: '#000000',
      secondary: '#A1A8B3',
      inverse: '#FFFFFF',
      link: '#FD5108',
    },
    surface: {
      page: '#FFFFFF',
      subtle: '#EEEFF1',
      card: '#FFFFFF',
      input: '#FFFFFF',
    },
    border: {
      default: '#DFE3E6',
      subtle: '#CBD1D6',
      strong: '#000000',
      disabled: '#B5BCC4',
    },
    state: {
      success: {
        fg: '#22C55E',
        bg: '#DCFCE7',
      },
      warning: {
        fg: '#EAB308',
        bg: '#FEF3C7',
      },
      error: {
        fg: '#EF4444',
        bg: '#FEE2E2',
      },
      info: {
        fg: '#3B82F6',
        bg: '#DBEAFE',
      },
    },
    dataViz: {
      seriesPrimary: '#FD5108',
      seriesSecondary: '#FFAA72',
      seriesTertiary: '#B5BCC4',
      gridLine: '#DFE3E6',
      axisText: '#A1A8B3',
    },
    darkMode: {
      surfacePage: '#1A1A1A',
      surfaceCard: '#242424',
      textPrimary: '#FFFFFF',
      textSecondary: '#B5BCC4',
      border: '#333333',
      inputBg: '#333333',
    },
  },
  typography: {
    fontFamily: {
      base: 'system-ui, sans-serif',
      mono:
        'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
      allowThemeOverride: true,
    },
    fontSizePx: {
      h1: 32,
      h2: 24,
      h3: 18,
      h4: 16,
      body: 14,
      labelMin: 12,
      labelMax: 13,
      micro: 11,
    },
    fontWeight: {
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      base: 1.5,
    },
  },
  spacingPx: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    '2xl': 48,
  },
  radiusPx: {
    none: 0,
    sm: 4,
    md: 6,
    lg: 8,
    pill: 12,
    round: 9999,
  },
  shadow: {
    level1: '0 1px 2px rgba(0,0,0,0.06)',
    level2: '0 4px 12px rgba(0,0,0,0.10)',
  },
  motion: {
    durationMs: {
      fast: 180,
      base: 240,
      slow: 360,
    },
    easing: {
      standard: 'cubic-bezier(0.2, 0, 0, 1)',
    },
  },
  layout: {
    pageGutterPx: {
      min: 24,
      max: 32,
    },
    sectionGapPx: {
      min: 24,
      max: 32,
    },
    cardPaddingPx: 24,
    touchTargetPxMin: 44,
  },
  accessibility: {
    minContrastRatio: 4.5,
    primaryButtonRule: {
      backgroundMustBe: '#FFAA72',
      textMustBe: '#000000',
      neverUseOrange500AsButtonBgWithText: true,
    },
    focus: {
      required: true,
      ring: {
        style: 'solid',
        widthPx: 2,
        color: '#FD5108',
        offsetPx: 2,
      },
    },
  },
  iconography: {
    library: 'lucide-react',
    sizePx: {
      min: 14,
      default: 16,
      max: 20,
    },
    color: {
      secondary: '#A1A8B3',
      accent: '#FD5108',
      primaryText: '#000000',
    },
    recommended: [
      'Search',
      'User',
      'Bell',
      'Menu',
      'X',
      'Check',
      'ChevronDown',
      'ChevronRight',
      'AlertCircle',
      'CheckCircle',
      'Info',
      'Sparkles',
      'MoreHorizontal',
      'Settings',
      'FileText',
      'Link2',
      'ExternalLink',
      'Paperclip',
      'Mic',
    ],
  },
  componentDefaults: {
    button: {
      paddingPx: {
        y: 12,
        x: 24,
      },
      fontSizePx: 14,
      fontWeight: 600,
      radius: 'md',
      borderWidthPx: 1,
    },
    card: {
      paddingPx: 24,
      radius: 'lg',
      borderColor: '#DFE3E6',
      borderWidthPx: 1,
      shadow: 'level1',
    },
    panel: {
      radius: 'lg',
      borderColor: '#DFE3E6',
      borderWidthPx: 1,
      headerPaddingPx: {
        y: 16,
        x: 20,
      },
      contentPaddingPx: 20,
    },
    input: {
      paddingPx: 12,
      radius: 'sm',
      borderColor: '#DFE3E6',
      borderWidthPx: 1,
      fontSizePx: 14,
      backgroundColor: '#FFFFFF',
    },
    table: {
      headerBg: '#EEEFF1',
      headerText: '#A1A8B3',
      rowBorder: '#DFE3E6',
      cellPaddingPx: {
        y: 16,
        x: 16,
      },
      headerPaddingPx: {
        y: 12,
        x: 16,
      },
      selection: {
        useTintBg: true,
        tintBg: '#FFE8D4',
        indicatorColor: '#FD5108',
        indicatorWidthPx: 2,
      },
    },
    tabs: {
      activeText: '#FD5108',
      inactiveText: '#A1A8B3',
      activeIndicatorColor: '#FD5108',
      activeIndicatorHeightPx: 2,
    },
    badge: {
      radius: 'md',
      paddingPx: {
        y: 4,
        x: 12,
      },
      standard: {
        bg: '#FFE8D4',
        fg: '#FD5108',
      },
    },
    tooltip: {
      radius: 'sm',
      bg: '#000000',
      fg: '#FFFFFF',
      paddingPx: {
        y: 8,
        x: 12,
      },
      fontSizePx: 12,
    },
    drawer: {
      widthPx: 380,
      radius: 'lg',
      borderColor: '#DFE3E6',
      borderWidthPx: 1,
      shadow: 'level2',
    },
  },
  aiUx: {
    states: [
      'idle',
      'thinking',
      'streaming',
      'tool_use',
      'needs_user_input',
      'completed',
      'uncertain',
      'error',
      'refusal',
    ],
    responseStructure: {
      sections: ['answer', 'evidence_or_sources', 'assumptions_or_constraints'],
      whenNoSources: 'must_display_no_sources_indicator',
    },
    controls: {
      applyActions: {
        defaultPattern: 'preview_then_apply',
        requireConfirmationFor: [
          'writing_to_system_of_record',
          'persisting_changes',
          'sending_notifications',
          'creating_or_deleting_records',
        ],
      },
      edits: {
        diffViewRequiredFor: ['text_changes', 'code_changes', 'configuration_changes'],
        versioning: {
          storePriorVersion: true,
          allowRestore: true,
        },
      },
    },
    provenance: {
      showGeneratedBadge: true,
      showTimestamp: true,
      showModelOrTool: {
        userFacingDefault: false,
        internalRequired: true,
      },
    },
    latencyHandling: {
      preferSkeletons: true,
      allowCancel: true,
      streamingIndicatorRequired: true,
      retryPattern: 'inline_retry_with_error_context',
    },
    visualIdentity: {
      accentColor: '#FD5108',
      messageUserBg: '#EEEFF1',
      messageUserRadius: 'sm',
      messageAssistantBg: 'transparent',
      assistantMark: {
        allowSmallGradientAccents: true,
        gradientToken: 'color.brand.gradientPrimary',
      },
    },
  },
  gradientPolicy: {
    largeFillsDisallowed: true,
    allowedUseCases: [
      'logo_mark',
      'hero_moments',
      'small_ai_identity_elements',
      'tiny_badge_accent',
      'empty_state_illustration_accent',
    ],
  },
  selectionPolicy: {
    avoidOveruseOrange500: true,
    selectedState: {
      preferTintBackground: '#FFE8D4',
      useOrange500AsIndicatorOnly: true,
    },
  },
} as const;

export type DesignSystemTokens = typeof tokens;
