import * as knowledgeService from './knowledgeService.js';
import * as leadManager from './leadManager.js';

// Gemini client initialization is entirely handled server-side now.
let aiClient = null;

async function generateContentWithFallback(params) {
  const response = await fetch('/api/method/dhanada.api.chatbot_response', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      conversation_history: params.contents,
      system_instruction: params.systemInstruction
    })
  });

  if (!response.ok) {
    throw new Error('Failed to reach Frappe API');
  }

  const data = await response.json();

  if (data.message && data.message.success) {
    return { text: data.message.message };
  } else {
    throw new Error(data.message?.message || "Gemini processing failed on server");
  }
}

const LEAD_STEPS = {
  NONE: 'none',
  PENDING_OFFER: 'pending_offer',
  CHOOSE_SHARE: 'choose_share',
  PHONE_ONLY: 'phone_only',
  EMAIL_ONLY: 'email_only',
  ASK_OPTIONAL_EMAIL: 'ask_optional_email',
  ASK_OPTIONAL_PHONE: 'ask_optional_phone',
  PHONE_THEN_EMAIL_MODE_1: 'phone_then_email_mode_1',
  PHONE_THEN_EMAIL_MODE_2: 'phone_then_email_mode_2',
  NAME: 'name',
  DONE: 'done',
};

const GREETINGS = ['hi', 'hello', 'hey', 'good morning', 'good evening', 'good afternoon', 'namaste'];
const THANKS = ['thanks', 'thank you', 'thx', 'appreciate it'];
const AFFIRMATIVE = ['yes', 'yeah', 'sure', 'okay', 'ok', 'please do', 'go ahead', 'sounds good', 'yes please'];
const NEGATIVE = ['no', 'not now', 'no thanks', 'maybe later', 'not interested'];

const TOPIC_PATTERNS = [
  { type: 'recommendation', patterns: ['recommend', 'suggest', 'best fund', 'which fund', 'where should i invest'] },
  { type: 'comparison', patterns: ['compare', 'vs', 'difference between', 'better'] },
  { type: 'nav', patterns: ['nav', 'net asset value'] },
  { type: 'performance', patterns: ['performance', 'return', 'returns', 'cagr'] },
  { type: 'marketNews', patterns: ['market news', 'market update', 'market today', 'news'] },
  { type: 'fundDetails', patterns: ['fund details', 'scheme details'] },
  { type: 'amc', patterns: ['amc', 'fund house', 'asset management company'] },
  { type: 'risk', patterns: ['risk', 'risky', 'riskometer', 'volatility'] },
  { type: 'category', patterns: ['category', 'categories', 'large cap', 'flexi cap', 'hybrid', 'debt fund', 'elss'] },
  { type: 'sip', patterns: ['sip', 'systematic investment'] },
  { type: 'lumpsum', patterns: ['lumpsum', 'lump sum', 'one time investment'] },
  { type: 'taxation', patterns: ['tax', 'taxation', 'capital gains'] },
  { type: 'assetAllocation', patterns: ['asset allocation', 'allocation'] },
  { type: 'portfolio', patterns: ['portfolio', 'holdings'] },
  { type: 'exitLoad', patterns: ['exit load'] },
  { type: 'expenseRatio', patterns: ['expense ratio', 'fund fee'] },
  { type: 'kyc', patterns: ['kyc', 'know your customer'] },
  { type: 'distributors', patterns: ['distributor', 'advisor near me', 'agent near me'] },
  { type: 'dhanadaServices', patterns: ['dhanada', 'your services', 'what do you offer', 'services'] },
  { type: 'sif', patterns: ['sif', 'specialised investment fund', 'specialized investment fund'] },
  { type: 'mutualFunds', patterns: ['mutual fund', 'mutual funds'] },
  { type: 'advisorRequest', patterns: ['call me', 'contact me', 'advisor', 'reach out', 'connect me'] },
];

const DEFAULT_QUICK_REPLIES = [
  'Explain SIP vs lumpsum',
  'Compare two funds',
  'Show sample NAV',
  'Help me choose a fund',
];

function normalizeText(value) {
  return String(value || '').toLowerCase().trim();
}

function matchesShortReply(text, phrases) {
  const cleanText = text.replace(/[^a-z0-9]+/g, ' ').trim();
  return phrases.some((phrase) => cleanText === phrase);
}

function extractProfile(state, message) {
  const text = normalizeText(message);
  const profile = { ...state.profile };

  if (text.includes('retirement')) profile.goal = 'retirement';
  if (text.includes('education')) profile.goal = 'education';
  if (text.includes('tax')) profile.goal = 'tax saving';
  if (text.includes('wealth')) profile.goal = 'wealth creation';
  if (text.includes('house')) profile.goal = 'house purchase';

  if (text.includes('conservative') || text.includes('low risk')) profile.risk = 'conservative';
  if (text.includes('moderate') || text.includes('balanced')) profile.risk = 'moderate';
  if (text.includes('aggressive') || text.includes('high risk')) profile.risk = 'aggressive';

  if (text.includes('sip')) profile.mode = 'sip';
  if (text.includes('lumpsum') || text.includes('lump sum')) profile.mode = 'lumpsum';

  const yearsMatch = text.match(/(\d+)\s*(year|years|yr|yrs)/);
  if (yearsMatch) {
    profile.horizonYears = Number(yearsMatch[1]);
  }

  const hasAmountCue =
    /(?:rs\.?|inr|₹|lakh|lakhs|thousand|amount|invest|investment|monthly|month)/.test(text);
  const amountMatch = text.match(/(?:rs\.?|inr|₹)?\s*([0-9]+(?:\.[0-9]+)?)\s*(lakh|lakhs|k|thousand)?/);
  if (hasAmountCue && amountMatch) {
    const base = Number(amountMatch[1]);
    const unit = amountMatch[2];

    if (unit === 'lakh' || unit === 'lakhs') profile.amount = base * 100000;
    else if (unit === 'k' || unit === 'thousand') profile.amount = base * 1000;
    else if (base >= 500) profile.amount = base;
  }

  state.profile = profile;
}

function formatComparison(result) {
  const [first, second] = result.funds;

  return [
    `${first.name} vs ${second.name}:`,
    `Category: ${first.category} vs ${second.category}`,
    `Risk: ${first.risk} vs ${second.risk}`,
    `Expense ratio: ${first.expenseRatio} vs ${second.expenseRatio}`,
    `1Y return: ${first.performance.oneYear} vs ${second.performance.oneYear}`,
    `Exit load: ${first.exitLoad} vs ${second.exitLoad}`,
    result.summary,
  ].join('\n');
}

function formatRecommendation(result, profile) {
  const profileLineParts = [];

  if (profile.goal) profileLineParts.push(`goal: ${profile.goal}`);
  if (profile.risk) profileLineParts.push(`risk: ${profile.risk}`);
  if (profile.horizonYears) profileLineParts.push(`horizon: ${profile.horizonYears} years`);
  if (profile.mode) profileLineParts.push(`mode: ${profile.mode}`);

  const heading = profileLineParts.length
    ? `Based on your ${profileLineParts.join(', ')}, here is a good starting point:`
    : 'Here is a good sample starting point:';

  const fundLines = result.suggestions
    .map((fund) => `• ${fund.name} - ${fund.category}, ${fund.risk} risk, suitable for ${fund.suitableFor.toLowerCase()}`)
    .join('\n');

  const rationale = result.rationale.map((item) => `• ${item}`).join('\n');

  return [heading, fundLines, '', rationale, '', result.summary].join('\n');
}

function chooseOffer(state) {
  return null;
}

function getQuickReplies(state) {
  if (state.leadStep === LEAD_STEPS.PENDING_OFFER) {
    return ['✅ Yes', '❌ Not now'];
  }

  if (state.leadStep === LEAD_STEPS.CHOOSE_SHARE) {
    return ['📱 Mobile Number', '✉️ Email Address', '📱+✉️ Both'];
  }

  if (state.leadStep === LEAD_STEPS.ASK_OPTIONAL_EMAIL || state.leadStep === LEAD_STEPS.ASK_OPTIONAL_PHONE) {
    return ['Yes', 'Skip'];
  }

  if (state.leadStep === LEAD_STEPS.NAME || state.leadStep === LEAD_STEPS.PHONE_ONLY || state.leadStep === LEAD_STEPS.EMAIL_ONLY || state.leadStep === LEAD_STEPS.PHONE_THEN_EMAIL_MODE_1 || state.leadStep === LEAD_STEPS.PHONE_THEN_EMAIL_MODE_2) {
    return [];
  }

  if (state.awaitingRecommendationDetails) {
    return ['Moderate risk', '5 year horizon', 'Monthly SIP'];
  }

  if (state.currentTopic === 'comparison') {
    return ['Compare Horizon vs Cedar', 'Compare Zenith vs Prism', 'Show sample NAV'];
  }

  if (state.currentTopic === 'sip') {
    return ['How SIP works', 'SIP vs lumpsum', 'Best fund for SIP'];
  }

  return DEFAULT_QUICK_REPLIES;
}

class SessionStore {
  constructor() {
    this.sessions = new Map();
  }

  get(sessionId) {
    if (!this.sessions.has(sessionId)) {
      this.sessions.set(sessionId, {
        history: [],
        turnCount: 0,
        currentTopic: null,
        helpfulTurns: 0,
        advisorOffered: false,
        advisorDeclined: false,
        lastOfferTurn: 0,
        leadStep: LEAD_STEPS.NONE,
        pendingOffer: false,
        leadCaptured: false,
        crmLeadName: null,
        collected: {
          name: null,
          phone: null,
          email: null,
        },
        profile: {
          goal: null,
          risk: null,
          horizonYears: null,
          amount: null,
          mode: null,
        },
        awaitingRecommendationDetails: false,
      });
    }

    return this.sessions.get(sessionId);
  }
}

export class Chatbot {
  constructor({ sessionStore = new SessionStore() } = {}) {
    this.sessionStore = sessionStore;
    this.sessionQueue = new Map();
  }

  async processMessage(sessionId, message) {
    const previousTask = this.sessionQueue.get(sessionId) || Promise.resolve();
    const currentTask = previousTask.catch(() => { }).then(() => this.processMessageInternal(sessionId, message));

    this.sessionQueue.set(sessionId, currentTask);

    try {
      return await currentTask;
    } finally {
      if (this.sessionQueue.get(sessionId) === currentTask) {
        this.sessionQueue.delete(sessionId);
      }
    }
  }

  async processMessageInternal(sessionId, message) {
    const state = this.sessionStore.get(sessionId);
    const cleanMessage = String(message || '').trim();

    // 1. Scan for explicit financial entity
    const explicitEntity = this.extractExplicitEntity(cleanMessage);

    // 2. If found and different from current topic, override previous conversation topic and context
    if (explicitEntity && explicitEntity !== state.currentTopic) {
      state.currentTopic = explicitEntity;
      // 3. Do not reuse stored conversation context for new entities
      state.history = [];
    }

    state.turnCount += 1;
    state.history.push({
      role: 'user',
      text: cleanMessage,
      at: new Date().toISOString(),
    });

    const intent = this.detectIntent(cleanMessage);
    const isNewTopic = !['unknown', 'affirmative', 'negative', 'thanks'].includes(intent);

    let reply;

    if (state.leadStep !== LEAD_STEPS.NONE && state.leadStep !== LEAD_STEPS.DONE) {
      if (state.leadStep === LEAD_STEPS.PENDING_OFFER && intent === 'negative') {
        state.leadStep = LEAD_STEPS.NONE;
        state.advisorOffered = false;
        state.helpfulTurns = -2;
        reply = 'No problem! I am here if you have more questions.';
      } else if (state.leadStep === LEAD_STEPS.PENDING_OFFER && intent === 'affirmative') {
        if (!state.collected.name) {
          state.leadStep = LEAD_STEPS.NAME;
          reply = 'Great! To start, what name should I tell our advisor?';
        } else {
          state.leadStep = LEAD_STEPS.CHOOSE_SHARE;
          if (!state.collected.phone && !state.collected.email) {
            reply = 'Great! To help our advisor connect with you, what would you like to share?';
          } else if (state.collected.phone && !state.collected.email) {
            state.leadStep = LEAD_STEPS.ASK_OPTIONAL_EMAIL;
            reply = `Great! Since we already have your phone number, would you also like to share your email address?`;
          } else if (state.collected.email && !state.collected.phone) {
            state.leadStep = LEAD_STEPS.ASK_OPTIONAL_PHONE;
            reply = `Great! Since we already have your email address, would you also like to share your mobile number?`;
          } else {
            // Should not happen since we don't offer if both are known, but just in case
            reply = await this.saveCompletedLead(state);
          }
        }
      }
    }

    if (state.awaitingRecommendationDetails && isNewTopic) {
      state.awaitingRecommendationDetails = false;
    }

    if (!reply) {
      if (!cleanMessage) {
        reply = 'Please type your question and I will help.';
      } else if (state.leadStep !== LEAD_STEPS.NONE && state.leadStep !== LEAD_STEPS.DONE) {
        const isInterruption = this.isLeadInterruption(state, cleanMessage, intent, explicitEntity);
        if (isInterruption) {
          reply = await this.handleIntent(state, cleanMessage);

          state.leadInterruptionTurns = (state.leadInterruptionTurns || 0) + 1;
          if (state.leadInterruptionTurns === 1 || state.leadInterruptionTurns % 3 === 0) {
            reply += '\n\n' + this.getLeadReminder(state);
          }
        } else {
          state.leadInterruptionTurns = 0;
          reply = await this.continueLeadFlow(state, cleanMessage, intent);
        }
      } else if (state.awaitingRecommendationDetails) {
        extractProfile(state, cleanMessage);
        reply = this.handleRecommendation(state);
      } else {
        extractProfile(state, cleanMessage);
        reply = await this.handleIntent(state, cleanMessage);
      }
    }


    state.history.push({
      role: 'bot',
      text: reply,
      at: new Date().toISOString(),
    });

    if (state.history.length > 40) {
      state.history = state.history.slice(-40);
    }

    return {
      reply,
      history: state.history,
      state: this.publicState(state),
      quickReplies: getQuickReplies(state),
    };
  }

  publicState(state) {
    return {
      helpfulTurns: state.helpfulTurns,
      currentTopic: state.currentTopic,
      leadStep: state.leadStep,
      leadCaptured: state.leadCaptured,
      collected: {
        name: state.collected.name,
        phone: state.collected.phone,
        email: state.collected.email,
      },
      profile: state.profile,
      pendingOffer: state.pendingOffer ? state.pendingOffer.id : null,
    };
  }

  detectIntent(message) {
    const text = normalizeText(message);

    if (matchesShortReply(text, GREETINGS)) return 'greeting';
    if (matchesShortReply(text, THANKS)) return 'thanks';
    if (matchesShortReply(text, AFFIRMATIVE)) return 'affirmative';
    if (matchesShortReply(text, NEGATIVE)) return 'negative';

    // Classify user intent before routing
    const words = text.split(/\s+/);
    const isShortQuery = words.length <= 2;
    const isInformational = /^(please\s+)?(can you\s+)?(could you\s+)?(just\s+)?(what is|what are|define|explain|tell me about|meaning of|what does|details of|information about|what's)\b/i.test(text);

    // If it's asking for guidance, recommendations, actions, comparisons, etc., route to Gemini
    if (!isInformational && !isShortQuery) {
      return 'unknown';
    }

    // If it's a purely informational definition or a short keyword lookup, use the local knowledge base
    for (const item of TOPIC_PATTERNS) {
      if (item.patterns.some((pattern) => text.includes(pattern))) {
        return item.type;
      }
    }

    if (knowledgeService.getFundDetails(message).status === 'ok') {
      return 'fundDetails';
    }

    return 'unknown';
  }

  extractExplicitEntity(text) {
    const skipList = ['greeting', 'thanks', 'affirmative', 'negative', 'advisorRequest', 'dhanadaServices', 'recommendation', 'comparison'];
    const lowerText = text.toLowerCase();

    // First, scan existing TOPIC_PATTERNS
    for (const item of TOPIC_PATTERNS) {
      if (skipList.includes(item.type)) continue;

      for (const pattern of item.patterns) {
        if (pattern.length <= 3) {
          if (new RegExp(`\\b${pattern}\\b`, 'i').test(text)) return item.type;
        } else {
          if (lowerText.includes(pattern)) return item.type;
        }
      }
    }

    // Scan additional keywords requested by user
    const extraEntities = ['fd', 'fixed deposit', 'equity', 'debt', 'mid cap', 'small cap', 'tax saving'];
    for (const entity of extraEntities) {
      if (entity.length <= 3) {
        if (new RegExp(`\\b${entity}\\b`, 'i').test(text)) return entity;
      } else {
        if (lowerText.includes(entity)) return entity;
      }
    }

    return null;
  }

  isLeadInterruption(state, message, intent, explicitEntity) {
    if (state.leadStep === LEAD_STEPS.NONE || state.leadStep === LEAD_STEPS.DONE) return false;

    // Explicit negatives cancel the flow, they don't interrupt it.
    if (intent === 'negative') return false;

    if (explicitEntity) return true;
    if (intent !== 'unknown' && intent !== 'affirmative' && intent !== 'thanks') return true;

    const text = message.toLowerCase().trim();
    if (text.includes('?')) return true;

    const questionWords = /^(what|how|why|when|where|who|is|are|can|could|would|should|do|does|did|tell|explain|compare|show|help)\b/i;
    if (questionWords.test(text)) return true;

    // If we are expecting a name, and they type more than 4 words, it's probably not a name.
    if (state.leadStep === LEAD_STEPS.NAME && text.split(/\s+/).length > 4) return true;

    return false;
  }

  getLeadReminder(state) {
    if (state.leadStep === LEAD_STEPS.NAME) {
      return 'Whenever you’re ready, I just need your name to continue your advisor request 😊';
    } else if (state.leadStep === LEAD_STEPS.CONTACT_PREF) {
      return 'We can continue with your advisor request whenever you’re ready. Just let me know if you prefer a phone call or email.';
    } else if (state.leadStep === LEAD_STEPS.PHONE) {
      return 'You had requested a callback earlier. Just share your phone number whenever convenient.';
    } else if (state.leadStep === LEAD_STEPS.EMAIL) {
      return 'Just share your email address whenever you’re ready to continue your advisor request.';
    } else if (state.leadStep === LEAD_STEPS.PHONE_THEN_EMAIL) {
      return 'You had requested an advisor earlier. Just share your phone number whenever convenient.';
    }
    return 'We can continue with your advisor request whenever you’re ready.';
  }

  async handleIntent(state, message) {
    const intent = this.detectIntent(message);

    if (intent !== 'unknown') {
      console.log(`[LOCAL] Responding to intent: ${intent}`);
    }

    switch (intent) {
      case 'greeting':
        return 'Hi! I am Dhanada, your investment assistant. How can I help you today?';

      case 'thanks':
        return 'Happy to help 😊';

      case 'affirmative':
        return 'Great! What would you like to explore next?';

      case 'negative':
        return 'No problem 😊';

      case 'recommendation':
        state.currentTopic = 'recommendation';
        return this.handleRecommendation(state);

      case 'comparison':
        state.currentTopic = 'comparison';
        return this.answerAndMaybeOffer(state, message, intent, this.handleComparison(message));

      case 'nav':
        state.currentTopic = 'nav';
        return this.answerAndMaybeOffer(state, message, intent, this.handleNAV(message));

      case 'performance':
        state.currentTopic = 'performance';
        return this.answerAndMaybeOffer(state, message, intent, this.handlePerformance(message));

      case 'marketNews':
        state.currentTopic = 'marketNews';
        return this.answerAndMaybeOffer(state, message, intent, this.handleMarketNews());

      case 'fundDetails':
        state.currentTopic = 'fundDetails';
        return this.answerAndMaybeOffer(state, message, intent, this.handleFundDetails(message));

      case 'amc':
        state.currentTopic = 'amc';
        return this.answerAndMaybeOffer(state, message, intent, this.handleAMC(message));

      case 'risk':
        state.currentTopic = 'risk';
        return this.answerAndMaybeOffer(state, message, intent, this.handleRisk(message));

      case 'category':
        state.currentTopic = 'category';
        return this.answerAndMaybeOffer(state, message, intent, this.handleCategory(message));

      case 'sip':
        state.currentTopic = 'sip';
        return this.answerAndMaybeOffer(state, message, intent, this.handleGuide('sip'));

      case 'lumpsum':
        state.currentTopic = 'lumpsum';
        return this.answerAndMaybeOffer(state, message, intent, this.handleGuide('lumpsum'));

      case 'taxation':
        state.currentTopic = 'taxation';
        return this.answerAndMaybeOffer(state, message, intent, this.handleGuide('taxation'));

      case 'assetAllocation':
        state.currentTopic = 'assetAllocation';
        return this.answerAndMaybeOffer(state, message, intent, this.handleGuide('assetAllocation'));

      case 'portfolio':
        state.currentTopic = 'portfolio';
        return this.answerAndMaybeOffer(state, message, intent, this.handleGuide('portfolio'));

      case 'exitLoad':
        state.currentTopic = 'exitLoad';
        return this.answerAndMaybeOffer(state, message, intent, this.handleGuide('exitLoad'));

      case 'expenseRatio':
        state.currentTopic = 'expenseRatio';
        return this.answerAndMaybeOffer(state, message, intent, this.handleGuide('expenseRatio'));

      case 'kyc':
        state.currentTopic = 'kyc';
        return this.answerAndMaybeOffer(state, message, intent, this.handleGuide('kyc'));

      case 'distributors':
        state.currentTopic = 'distributors';
        return this.answerAndMaybeOffer(state, message, intent, this.handleDistributors(message));

      case 'dhanadaServices':
        state.currentTopic = 'dhanadaServices';
        return this.answerAndMaybeOffer(state, message, intent, this.handleServices());

      case 'sif':
        state.currentTopic = 'sif';
        return this.answerAndMaybeOffer(state, message, intent, this.handleGuide('sif'));

      case 'mutualFunds':
        state.currentTopic = 'mutualFunds';
        return this.answerAndMaybeOffer(state, message, intent, this.handleGuide('mutualFunds'));

      case 'advisorRequest':
        state.currentTopic = 'dhanadaServices';
        if (!state.collected.name) {
          state.leadStep = LEAD_STEPS.NAME;
          return 'I can arrange that. May I know your name?';
        } else if (!state.collected.phone) {
          state.leadStep = LEAD_STEPS.PHONE;
          return `I can arrange that. Could you share your mobile number?`;
        } else if (!state.collected.email) {
          state.leadStep = LEAD_STEPS.EMAIL;
          return `I can arrange that. Could you also share your email address?`;
        } else {
          return 'Our advisor will connect with you shortly!';
        }

      default:
        return await this.handleUnknown(state, message);
    }
  }

  answerAndMaybeOffer(state, message, intent, answer) {
    if (state.leadStep !== LEAD_STEPS.NONE && state.leadStep !== LEAD_STEPS.DONE) {
      return `${answer}\n\n${this.getLeadReminder(state)}`;
    }

    if (!this.shouldOfferLead(state, message, intent)) {
      return answer;
    }

    state.advisorOffered = true;
    state.lastOfferTurn = state.turnCount;
    state.leadStep = LEAD_STEPS.PENDING_OFFER;

    let leadQuestion = "Would you like me to connect you with one of our investment advisors?";

    if (intent === 'recommendation' || intent === 'comparison') {
      leadQuestion = "I can also help you narrow down suitable options for your specific goals. Would you like an advisor to contact you?";
    } else if (state.profile.amount || state.profile.mode === 'sip') {
      const amountStr = state.profile.amount ? ` ₹${state.profile.amount.toLocaleString('en-IN')}` : '';
      const modeStr = state.profile.mode === 'sip' ? ' SIP' : ' investment';
      leadQuestion = `If you're planning to start a${amountStr}${modeStr}, I can help you understand which option may suit your goals. Would you like an advisor to assist you?`;
    } else if (state.currentTopic === 'sif') {
      leadQuestion = "If you're considering investing in a SIF, I can help you understand which option may suit your goals. Would you like an advisor to contact you?";
    }

    return `${answer}\n\n${leadQuestion}`;
  }

  shouldOfferLead(state, message, intent) {
    if (state.leadCaptured) return false;
    if (state.advisorOffered) return false;
    if (state.collected.phone && state.collected.email) return false;
    if (state.leadStep !== LEAD_STEPS.NONE && state.leadStep !== LEAD_STEPS.DONE) return false;

    if (intent === 'advisorRequest') return true;
    if (intent === 'recommendation') return true;
    if (intent === 'comparison') return true;

    if (state.profile.amount || state.profile.goal || state.profile.horizonYears) return true;

    const lowerMessage = String(message || '').toLowerCase();
    const buyingIntent = /(want to invest|how to invest|start sip|choose a fund|help me choose|looking to invest)/.test(lowerMessage);
    if (buyingIntent) return true;

    return false;
  }

  handleGuide(key) {
    const guide = knowledgeService.getGuideByKey(key);

    if (!guide) {
      return 'I can explain that topic in simple terms if you tell me the exact area.';
    }

    return `${guide.title}: ${guide.summary}`;
  }

  handleFundDetails(message) {
    const result = knowledgeService.getFundDetails(message);

    if (result.status !== 'ok') {
      return `${result.message}\nSample schemes: ${result.availableFunds.join(', ')}`;
    }

    const { fund } = result;
    return [
      `${fund.name}:`,
      `Category: ${fund.category}`,
      `AMC: ${fund.amc}`,
      `Risk: ${fund.risk}`,
      `Expense ratio: ${fund.expenseRatio}`,
      `Exit load: ${fund.exitLoad}`,
      `Best fit: ${fund.suitableFor}`,
      result.note,
    ].join('\n');
  }

  handleNAV(message) {
    const result = knowledgeService.getNAV(message);

    if (result.status !== 'ok') {
      return `${result.message}\nSample schemes: ${result.availableFunds.join(', ')}`;
    }

    return `${result.fundName} has a sample NAV of ${result.nav} as of ${result.asOf}. ${result.note}`;
  }

  handleAMC(message) {
    const result = knowledgeService.getAMC(message);

    if (result.status !== 'ok') {
      return `${result.message}\nSample AMCs: ${result.availableAMCs.join(', ')}`;
    }

    return [
      `${result.amc.name}: ${result.amc.summary}`,
      `Strengths: ${result.amc.strengths.join(', ')}`,
    ].join('\n');
  }

  handleRisk(message) {
    const result = knowledgeService.getRisk(message);

    if (result.mode === 'fund') {
      return result.summary;
    }

    return `A simple risk view:\n${result.bands.map((item) => `• ${item}`).join('\n')}`;
  }

  handleCategory(message) {
    const result = knowledgeService.getCategory(message);

    if (result.category) {
      return `${String(result.category).toUpperCase()}: ${result.summary}`;
    }

    return `${result.summary}\nCommon options: ${result.categories.join(', ')}`;
  }

  handlePerformance(message) {
    const result = knowledgeService.getPerformance(message);

    if (result.status !== 'ok') {
      return `${result.message}\nSample schemes: ${result.availableFunds.join(', ')}`;
    }

    return [
      `${result.fundName} sample performance:`,
      `1Y: ${result.performance.oneYear}`,
      `3Y: ${result.performance.threeYear}`,
      `5Y: ${result.performance.fiveYear}`,
      result.note,
    ].join('\n');
  }

  handleMarketNews() {
    const result = knowledgeService.getMarketNews();
    const items = result.items.map((item) => `• ${item.headline}: ${item.summary}`).join('\n');
    return `Sample market snapshot as of ${result.asOf}:\n${items}\n${result.note}`;
  }

  handleDistributors(message) {
    const result = knowledgeService.getDistributor(message);
    return `Here are sample Dhanada advisor options for ${result.city}:\n${result.options.map((item) => `• ${item}`).join('\n')}`;
  }

  handleServices() {
    const result = knowledgeService.getPlatformOverview();
    return `${result.summary}\nServices:\n${result.services.map((item) => `• ${item}`).join('\n')}`;
  }

  handleComparison(message) {
    const result = knowledgeService.compareFunds(message);

    if (result.status !== 'ok') {
      return `${result.message}\nSample schemes: ${result.availableFunds.join(', ')}`;
    }

    return formatComparison(result);
  }

  handleRecommendation(state) {
    const profile = state.profile;

    if (!profile.risk || !profile.horizonYears) {
      state.awaitingRecommendationDetails = true;
      return 'I can help with that. Please share your risk level and time horizon, for example: moderate risk, 5 years, SIP.';
    }

    state.awaitingRecommendationDetails = false;
    const result = knowledgeService.getRecommendation(profile);
    return this.answerAndMaybeOffer(state, "recommendation", "recommendation", formatRecommendation(result, profile));
  }

  async handleUnknown(state, message) {
    if (state.currentTopic === 'recommendation') {
      return 'Please share your risk level and horizon so I can make a good suggestion 😊';
    }

    const localFallback = 'I can help with SIP, mutual funds, risk, tax, and more. What would you like to know?';

    try {
      const systemInstruction = `You are Dhanada, a friendly, professional investment assistant for Dhanada Specialized Investment Fund.
Answer questions about Mutual Funds, SIP, NAV, Tax, Risk, Asset Allocation, Retirement, Investing, Wealth Creation, Financial Planning, and General Finance.
Default to short, conversational, and concise responses (1-3 short sentences).
Keep responses mobile-friendly. Avoid verbose explanations, long disclaimers, unnecessary introductions, or conclusions.
Do not repeat information already given earlier in the conversation.
Use bullet points only when genuinely helpful.
ONLY provide a longer, detailed response if the user explicitly asks to "Explain in detail", "Tell me more", "Complete comparison", or "Detailed analysis".
NEVER mention AI, Gemini, or that you are a large language model.
If the user asks something completely unrelated to finance, politely steer them back.`;

      const contents = state.history.map(msg => ({
        role: msg.role === 'user' ? 'user' : 'model',
        parts: [{ text: msg.text }]
      }));

      const response = await generateContentWithFallback({
        systemInstruction,
        contents,
      });

      return this.answerAndMaybeOffer(state, message, "unknown", response.text);
    } catch (error) {
      console.error('[GEMINI ERROR]:', error.message);
      const fallbackReply = "I'm having trouble connecting right now, but " + localFallback;
      return this.answerAndMaybeOffer(state, message, "unknown", fallbackReply);
    }
  }

  async continueLeadFlow(state, message, intent) {
    if (state.leadStep === LEAD_STEPS.CHOOSE_SHARE) {
      if (message.includes('both') || message.includes('Both')) {
        state.leadStep = LEAD_STEPS.PHONE_THEN_EMAIL_MODE_1;
        return 'Great! Could you share your mobile number first?';
      } else if (message.includes('mail') || message.includes('Email')) {
        state.leadStep = LEAD_STEPS.EMAIL_ONLY;
        return 'Great! Could you share your email address?';
      } else {
        state.leadStep = LEAD_STEPS.PHONE_ONLY;
        return 'Great! Could you share your mobile number?';
      }
    }

    if (state.leadStep === LEAD_STEPS.NAME) {
      const nameCheck = leadManager.validateName(message);
      if (!nameCheck.valid) {
        return `${nameCheck.message}\nMay I know your name?`;
      }
      state.collected.name = nameCheck.value;
      state.leadStep = LEAD_STEPS.CHOOSE_SHARE;
      return `Nice to meet you, ${state.collected.name}! To help our advisor connect with you, what would you like to share?`;
    }

    if (state.leadStep === LEAD_STEPS.PHONE_ONLY || state.leadStep === LEAD_STEPS.PHONE_THEN_EMAIL_MODE_1 || state.leadStep === LEAD_STEPS.PHONE_THEN_EMAIL_MODE_2 || state.leadStep === LEAD_STEPS.ASK_OPTIONAL_PHONE) {
      if (state.leadStep === LEAD_STEPS.ASK_OPTIONAL_PHONE && (intent === 'negative' || message.toLowerCase().trim() === 'skip')) {
        return await this.saveCompletedLead(state);
      }

      const phoneCheck = leadManager.validatePhone(message);
      if (!phoneCheck.valid) {
        return `${phoneCheck.message}\nPlease share your 10-digit mobile number.`;
      }
      state.collected.phone = phoneCheck.value;

      if (state.leadStep === LEAD_STEPS.PHONE_THEN_EMAIL_MODE_1 || state.leadStep === LEAD_STEPS.PHONE_THEN_EMAIL_MODE_2) {
        state.leadStep = LEAD_STEPS.ASK_OPTIONAL_EMAIL;
        return 'Thank you. Could you also share your email address?';
      }

      if (state.leadStep === LEAD_STEPS.PHONE_ONLY && !state.collected.email) {
        state.leadStep = LEAD_STEPS.ASK_OPTIONAL_EMAIL;
        return 'Thank you. Would you also like to share your email address?';
      }

      return await this.saveCompletedLead(state);
    }

    if (state.leadStep === LEAD_STEPS.EMAIL_ONLY || state.leadStep === LEAD_STEPS.ASK_OPTIONAL_EMAIL) {
      if (state.leadStep === LEAD_STEPS.ASK_OPTIONAL_EMAIL && (intent === 'negative' || message.toLowerCase().trim() === 'skip')) {
        return await this.saveCompletedLead(state);
      }

      const emailCheck = leadManager.validateEmail(message);
      if (!emailCheck.valid) {
        return `${emailCheck.message}\nPlease share a valid email address.`;
      }
      state.collected.email = emailCheck.value;

      if (state.leadStep === LEAD_STEPS.EMAIL_ONLY && !state.collected.phone) {
        state.leadStep = LEAD_STEPS.ASK_OPTIONAL_PHONE;
        return 'Thank you. Would you also like to share your mobile number?';
      }

      return await this.saveCompletedLead(state);
    }

    return await this.saveCompletedLead(state);
  }

  async saveCompletedLead(state) {
    if (!state.collected.phone && !state.collected.email) {
      state.leadStep = LEAD_STEPS.NONE;
      state.advisorOffered = false;
      return "I need either a phone number or an email to connect you with an advisor. Let me know if you change your mind.";
    }

    state.leadCaptured = true;
    state.leadStep = LEAD_STEPS.DONE;

    const chatSummary = state.history
      .map((msg) => `${msg.role.toUpperCase()}: ${msg.text}`)
      .join('\n');

    const leadData = {
      name: state.collected.name,
      phone: state.collected.phone,
      email: state.collected.email,
      interest: state.currentTopic || 'General Inquiry',
      chat_summary: chatSummary,
      source: 'Website Chatbot',
    };

    const result = await leadManager.saveLead(leadData);

    if (result.success) {
      state.crmLeadName = result.lead_name;
      return `Thank you, ${state.collected.name || ''}! I have passed your details to our team. An advisor will reach out to you shortly.`;
    } else {
      console.error('[CRM ERROR]', result.message);
      return `Thank you! I have noted your details. An advisor will reach out to you shortly. (Internal Note: CRM saving is temporarily delayed)`;
    }
  }
}
