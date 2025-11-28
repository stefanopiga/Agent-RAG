# docling-rag-agent UX Design Specification

_Created on 2025-11-26 by Stefano_
_Generated using BMad Method - Create UX Design Workflow v1.0_

---

## Executive Summary

**Vision:** Sistema RAG production-ready con observability completa, cost tracking e monitoring real-time per sviluppatori che integrano RAG nei loro workflow.

**Utenti Target:** Sviluppatori che usano MCP Server (programmatico) e Streamlit UI (interattivo)

**Esperienza Core:** Query conversazionali sulla knowledge base con risposte accurate e citazioni delle fonti

**Emozione Desiderata:** Efficienza/produttività + fiducia/affidabilità + controllo/chiarezza

**Piattaforma:** Streamlit (web-based Python framework) + MCP Server (API)

**Complessità UX:** Media (2 interfacce distinte, pattern standard chat + dashboard)

---

## 1. Design System Foundation

### 1.1 Design System Choice

**Sistema Scelto:** Streamlit Native Components + Custom CSS Minimale

**Versione:** Streamlit 1.31+ (componenti nativi)

**Componenti Forniti:**
- Chat interface: `st.chat_message`, `st.chat_input`
- Metriche: `st.metric`, `st.columns` per card layout
- Sidebar: `st.sidebar` nativo
- Data display: `st.dataframe`, `st.table` per metriche tabella
- Grafici: `st.plotly_chart`, `st.line_chart` per trend
- Layout: `st.columns`, `st.container` per organizzazione

**Customizzazione:**
- CSS minimale per branding e dark mode
- Theming via `st.markdown` con HTML/CSS inline
- Personalizzazione colori Streamlit con `st.set_page_config`

**Accessibilità:**
- WCAG AA compliance nativa Streamlit
- Keyboard navigation built-in
- Screen reader support automatico

**Rationale:**
- Zero dipendenze aggiuntive per componenti base
- Accessibilità garantita out-of-the-box
- Manutenzione minima
- Allineato con obiettivo efficienza/produttività
- CSS custom minimale sufficiente per branding e dark mode (ispirazione Gemini)

**Componenti Custom Necessari:**
- Nessuno per MVP (Streamlit nativo copre tutti i casi d'uso)
- Eventuale componente React futuro solo se necessario per funzionalità avanzate non supportate nativamente

---

## 2. Core User Experience

### 2.1 Defining Experience

**Esperienza Definitiva:** Sistema RAG che permette agli sviluppatori di fare query conversazionali sulla knowledge base ottenendo risposte accurate con citazioni delle fonti, mentre monitorano costi e performance in tempo reale.

**Core Action:** Query conversazionale → Risposta RAG con citazioni → Monitoring costi/performance

**Pattern Standard Applicabili:**
- Chat interface (pattern consolidato) - Streamlit `st.chat_message` + `st.chat_input`
- Dashboard analytics (pattern consolidato) - Streamlit `st.metric` + `st.columns`
- Real-time metrics display (pattern consolidato) - Streamlit `st.dataframe` con auto-refresh o `st.metric` cards

**Definizione Esperienza:**
Quando qualcuno descrive questo sistema, direbbe: "È il sistema RAG dove fai una domanda e ottieni una risposta precisa con le fonti, mentre vedi in tempo reale quanto costa ogni query e quanto è veloce."

**L'UNICA cosa che definisce l'app:**
La trasparenza totale: ogni query mostra costo, latenza e fonti utilizzate. Non è solo un chatbot RAG, è un sistema RAG osservabile dove ogni operazione è tracciata e visibile.

**Cosa rende questa esperienza unica:**
- Monitoring integrato nella UI (non separato)
- Cost tracking visibile durante l'uso (non solo in report)
- Citazioni fonti sempre presenti (non opzionali)

### 2.2 Novel UX Patterns

_Non rilevanti - pattern standard applicabili_

### 2.3 Core Experience Principles

**Principi Guida per l'Intera Esperienza:**

**1. Speed (Velocità):**
- Query devono completarsi in < 2 secondi (95th percentile)
- Feedback immediato durante elaborazione (loading states chiari)
- Metriche aggiornate in real-time senza refresh manuale
- Latency breakdown visibile per ogni componente (embedding, DB, LLM)

**2. Guidance (Guida):**
- Chat interface intuitiva senza tutorial necessario
- Metriche auto-esplicative con tooltip opzionali
- Error messages informativi con suggerimenti di recovery
- Citazioni fonti sempre visibili e cliccabili

**3. Flexibility (Flessibilità):**
- Supporto sia visualizzazione tabella che card per metriche (scelta utente)
- Sidebar collassabile per più spazio chat
- Dark mode toggle per preferenze utente
- Filtri opzionali per query avanzate (source_filter)

**4. Feedback (Feedback):**
- Feedback celebratorio per query di successo (subtle, non invasivo)
- Indicatori visivi chiari per stati (loading, success, error)
- Cost tracking sempre visibile ma non intrusivo
- Real-time updates senza interruzioni dell'esperienza utente

**Rationale:**
Questi principi bilanciano efficienza (speed), fiducia (guidance + feedback), e controllo (flexibility) - le tre emozioni target dell'esperienza.

---

## 3. Visual Foundation

### 3.2 Typography System

**Font Families:**
- **Headings & Body:** System font stack (-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell)
- **Monospace:** 'Courier New', monospace (per codice, hex codes, metriche tecniche)

**Type Scale:**
- **H1:** 2.5rem (40px) - Titoli principali
- **H2:** 1.8rem (28.8px) - Sezioni
- **H3:** 1.5rem (24px) - Sottosezioni
- **H4:** 1.25rem (20px) - Card titles
- **Body:** 1rem (16px) - Testo principale
- **Small:** 0.85rem (13.6px) - Label, metadata
- **Tiny:** 0.75rem (12px) - Tooltip, note

**Font Weights:**
- **700 (Bold):** Metriche, valori numerici importanti
- **600 (Semi-bold):** Titoli card, label importanti
- **500 (Medium):** Label form, navigation
- **400 (Regular):** Testo body, default

**Line Heights:**
- **Headings:** 1.2
- **Body:** 1.6
- **Dense (tabelle):** 1.4

**Rationale:**
- System fonts garantiscono performance e familiarità cross-platform
- Scale modulare per gerarchia visiva chiara
- Line heights ottimizzati per leggibilità su dark background

### 3.3 Spacing & Layout System

**Base Unit:** 4px

**Spacing Scale:**
- **xs:** 0.25rem (4px)
- **sm:** 0.5rem (8px)
- **md:** 1rem (16px)
- **lg:** 1.5rem (24px)
- **xl:** 2rem (32px)
- **2xl:** 3rem (48px)

**Layout Grid:**
- Streamlit nativo: `st.columns` per layout responsive
- Container max-width: 1400px per desktop
- Sidebar width: 300px (Streamlit default, collassabile)

**Breakpoints (Streamlit responsive):**
- Mobile: < 768px (single column)
- Tablet: 768px - 1024px (2 columns)
- Desktop: > 1024px (3+ columns)

**Rationale:**
- Scale 4px per consistenza visiva
- Streamlit gestisce responsive automaticamente
- Container width ottimizzato per dashboard analytics

### 3.1 Color System

**Tema Scelto:** Dark Purple Professional

**Palette Principale:**
- **Background:** `#0F0A1A` - Sfondo principale (quasi nero con sfumatura viola)
- **Surface:** `#1A0F2E` - Card e container
- **Primary Dark:** `#2D1B4E` - Bordi, elementi secondari
- **Primary:** `#805AD5` - Azioni primarie, link
- **Primary Light:** `#9F7AEA` - Hover states
- **Accent:** `#B794F6` - Titoli, enfasi

**Colori Testo:**
- **Text Primary:** `#E8E4F0` - Testo principale
- **Text Secondary:** `#A0AEC0` - Testo secondario
- **Text Muted:** `#718096` - Testo disabilitato

**Colori Semantici:**
- **Success:** `#68D391` - Query riuscite, metriche positive
- **Warning:** `#FBD68D` - Avvisi, latenza elevata
- **Error:** `#FC8181` - Errori query, fallimenti
- **Info:** `#90CDF4` - Informazioni, tooltip

**Rationale:**
- Viola scuro scuro riduce affaticamento visivo per uso prolungato
- Palette professionale ma distintiva, perfetta per tool enterprise
- Contrasto WCAG AA garantito (minimo 4.5:1 per testo)
- Colori semantici chiari per monitoring e alert
- Allineato con ispirazione Gemini app (dark mode, sidebar organizzata)

**Ispirazione:** Gemini app - sidebar organizzata, chat pulita, dark mode support

**Metriche Display Preferences:**
- Opzione A: Tabella con aggiornamento costante (real-time)
- Opzione B: Card separate, ognuna con il proprio indicatore
- Entrambe le opzioni supportate

**Interactive Visualizations:**

- Color Theme Explorer: [ux-color-themes.html](./ux-color-themes.html)

---

## 4. Design Direction

### 4.1 Chosen Design Approach

_To be defined in next step_

**Interactive Mockups:**

- Design Direction Showcase: [ux-design-directions.html](./ux-design-directions.html)

---

## 5. User Journey Flows

### 5.1 Critical User Paths

_To be defined in next step_

---

## 6. Component Library

### 6.1 Component Strategy

_To be defined in next step_

---

## 7. UX Pattern Decisions

### 7.1 Consistency Rules

_To be defined in next step_

---

## 8. Responsive Design & Accessibility

### 8.1 Responsive Strategy

_To be defined in next step_

---

## 9. Implementation Guidance

### 9.1 Completion Summary

_To be defined upon completion_

---

## Appendix

### Related Documents

- Product Requirements: `docs/prd.md`
- Architecture: `docs/architecture.md`
- Epics: `docs/epics.md`

### Core Interactive Deliverables

This UX Design Specification was created through visual collaboration:

- **Color Theme Visualizer**: [ux-color-themes.html](./ux-color-themes.html)
  - Interactive HTML showing all color theme options explored
  - Live UI component examples in each theme
  - Side-by-side comparison and semantic color usage

- **Design Direction Mockups**: [ux-design-directions.html](./ux-design-directions.html)
  - Interactive HTML with 6-8 complete design approaches
  - Full-screen mockups of key screens
  - Design philosophy and rationale for each direction

### Next Steps & Follow-Up Workflows

This UX Design Specification can serve as input to:

- **Wireframe Generation Workflow** - Create detailed wireframes from user flows
- **Figma Design Workflow** - Generate Figma files via MCP integration
- **Interactive Prototype Workflow** - Build clickable HTML prototypes
- **Component Showcase Workflow** - Create interactive component library
- **AI Frontend Prompt Workflow** - Generate prompts for v0, Lovable, Bolt, etc.
- **Solution Architecture Workflow** - Define technical architecture with UX context

### Version History

| Date     | Version | Changes                         | Author   |
| -------- | ------- | ------------------------------- | -------- |
| 2025-11-26 | 1.0     | Initial UX Design Specification | Stefano |

---

_This UX Design Specification was created through collaborative design facilitation, not template generation. All decisions were made with user input and are documented with rationale._

