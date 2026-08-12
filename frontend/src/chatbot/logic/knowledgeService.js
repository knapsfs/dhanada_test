'use strict';

const DEMO_DATE = 'July 30, 2026';

const TOPIC_GUIDES = {
  mutualFunds: {
    title: 'Mutual Funds',
    summary:
      'A mutual fund pools money from many investors and invests it across assets like equity, debt, or hybrids based on a defined objective.',
  },
  sif: {
    title: 'SIF',
    summary:
      'A Specialised Investment Fund sits between traditional mutual funds and more advanced products. It can use more flexible strategies and usually suits informed investors.',
  },
  sip: {
    title: 'SIP',
    summary:
      'A SIP is a fixed amount invested at regular intervals. It helps build discipline, smooth market entry, and is useful for long-term goals.',
  },
  lumpsum: {
    title: 'Lumpsum',
    summary:
      'A lumpsum is a one-time investment. It can work well when you already have a corpus and a long enough time horizon.',
  },
  nav: {
    title: 'NAV',
    summary:
      'NAV is the per-unit value of a mutual fund. It is calculated from total assets minus liabilities, divided by outstanding units.',
  },
  amc: {
    title: 'AMC',
    summary:
      'An AMC is the fund house that manages schemes, research, portfolio decisions, compliance, and investor servicing.',
  },
  risk: {
    title: 'Risk',
    summary:
      'Risk is the chance that actual returns differ from expected returns. In funds, common risks are market risk, credit risk, interest-rate risk, and liquidity risk.',
  },
  returns: {
    title: 'Returns',
    summary:
      'Returns show how much an investment gained or lost over time. It is better to read them with risk, category, and time horizon together.',
  },
  assetAllocation: {
    title: 'Asset Allocation',
    summary:
      'Asset allocation means splitting money across equity, debt, gold, and cash based on your goal, time horizon, and risk comfort.',
  },
  taxation: {
    title: 'Taxation',
    summary:
      'Mutual fund tax depends on fund type and holding period. It is best to confirm current tax rules before investing because regulations can change.',
  },
  portfolio: {
    title: 'Portfolio',
    summary:
      'A portfolio is the full mix of investments you hold. A good portfolio matches your goals, risk level, and liquidity needs.',
  },
  exitLoad: {
    title: 'Exit Load',
    summary:
      'Exit load is a fee charged when you redeem units before a scheme’s stated period. It is meant to discourage very short holding periods.',
  },
  expenseRatio: {
    title: 'Expense Ratio',
    summary:
      'Expense ratio is the yearly fee charged by the AMC to manage the fund. Lower cost is helpful, but it should be judged with process and consistency too.',
  },
  comparison: {
    title: 'Fund Comparison',
    summary:
      'A good fund comparison looks at category, risk, cost, consistency, asset mix, exit load, and whether the scheme fits your goal.',
  },
  investmentProcess: {
    title: 'Investment Process',
    summary:
      'The usual flow is KYC, goal mapping, scheme selection, SIP or lumpsum setup, transaction completion, and periodic review.',
  },
  kyc: {
    title: 'KYC',
    summary:
      'KYC is the identity verification required before investing. It usually needs PAN, Aadhaar, and basic address details.',
  },
  distributors: {
    title: 'Distributors',
    summary:
      'A distributor or advisor helps with fund selection, onboarding, and execution. The right one should match your goal and explain risk clearly.',
  },
  dhanadaServices: {
    title: 'Dhanada Services',
    summary:
      'Dhanada helps with fund research, goal planning, SIP setup, lump sum planning, KYC support, fund comparison, and advisor connection.',
  },
};

const FUNDS = [
  {
    name: 'Horizon Bluechip Fund',
    aliases: ['horizon bluechip', 'bluechip fund', 'bluechip'],
    category: 'Large Cap Equity',
    amc: 'Horizon AMC',
    risk: 'Moderately High',
    nav: 42.38,
    performance: { oneYear: '14.2%', threeYear: '17.8%', fiveYear: '15.9%' },
    expenseRatio: '1.12%',
    exitLoad: '1% if redeemed within 12 months',
    assetAllocation: '92% equity, 6% cash, 2% debt',
    suitableFor: 'Investors looking for large-cap exposure over 5 years or more.',
  },
  {
    name: 'Zenith Flexi Cap Fund',
    aliases: ['zenith flexi cap', 'flexi cap fund', 'flexi cap'],
    category: 'Flexi Cap Equity',
    amc: 'Zenith Mutual',
    risk: 'High',
    nav: 58.14,
    performance: { oneYear: '18.6%', threeYear: '20.2%', fiveYear: '18.1%' },
    expenseRatio: '1.25%',
    exitLoad: '1% if redeemed within 12 months',
    assetAllocation: '95% equity, 5% cash',
    suitableFor: 'Investors comfortable with higher volatility for long-term growth.',
  },
  {
    name: 'Cedar Balanced Advantage Fund',
    aliases: ['cedar balanced advantage', 'balanced advantage fund', 'balanced advantage'],
    category: 'Dynamic Hybrid',
    amc: 'Cedar AMC',
    risk: 'Moderate',
    nav: 31.72,
    performance: { oneYear: '11.4%', threeYear: '13.6%', fiveYear: '12.7%' },
    expenseRatio: '0.96%',
    exitLoad: 'Nil after 6 months',
    assetAllocation: '62% equity, 28% debt, 10% arbitrage and cash',
    suitableFor: 'Investors who want a smoother ride than pure equity.',
  },
  {
    name: 'Atlas Short Duration Debt Fund',
    aliases: ['atlas short duration debt', 'short duration debt fund', 'debt fund'],
    category: 'Short Duration Debt',
    amc: 'Atlas AMC',
    risk: 'Low to Moderate',
    nav: 18.49,
    performance: { oneYear: '7.1%', threeYear: '6.8%', fiveYear: '6.5%' },
    expenseRatio: '0.52%',
    exitLoad: 'Nil',
    assetAllocation: '88% debt, 12% cash and money market',
    suitableFor: 'Shorter horizon investors focused more on stability than growth.',
  },
  {
    name: 'Prism Tax Saver Fund',
    aliases: ['prism tax saver', 'tax saver fund', 'elss'],
    category: 'ELSS',
    amc: 'Prism Mutual',
    risk: 'High',
    nav: 24.67,
    performance: { oneYear: '16.5%', threeYear: '19.1%', fiveYear: '17.3%' },
    expenseRatio: '1.08%',
    exitLoad: 'Locked for 3 years as per ELSS rules',
    assetAllocation: '94% equity, 6% cash',
    suitableFor: 'Investors seeking equity exposure with tax-saving under ELSS rules.',
  },
];

const AMC_DETAILS = [
  {
    name: 'Horizon AMC',
    aliases: ['horizon amc', 'horizon'],
    summary: 'Known for large-cap research and disciplined portfolio construction.',
    strengths: ['Large-cap process', 'Risk controls', 'Stable investment team'],
  },
  {
    name: 'Zenith Mutual',
    aliases: ['zenith mutual', 'zenith'],
    summary: 'Focused on flexible equity strategies with active sector rotation.',
    strengths: ['Flexible mandate', 'Growth orientation', 'Broad market coverage'],
  },
  {
    name: 'Cedar AMC',
    aliases: ['cedar amc', 'cedar'],
    summary: 'Hybrid and asset-allocation focused fund house with balanced risk design.',
    strengths: ['Hybrid expertise', 'Downside control', 'Allocation discipline'],
  },
  {
    name: 'Atlas AMC',
    aliases: ['atlas amc', 'atlas'],
    summary: 'Debt-focused AMC with emphasis on duration control and high-quality issuers.',
    strengths: ['Debt quality', 'Liquidity focus', 'Short-duration management'],
  },
  {
    name: 'Prism Mutual',
    aliases: ['prism mutual', 'prism'],
    summary: 'Equity-led AMC with a strong tax-saving and core growth lineup.',
    strengths: ['ELSS range', 'Core equity process', 'Long-term orientation'],
  },
];

const CATEGORY_GUIDES = {
  'large cap': 'Large-cap funds invest in bigger, more established companies and are often used for core long-term equity allocation.',
  'flexi cap': 'Flexi-cap funds can move across large, mid, and small caps, giving the fund manager more freedom.',
  hybrid: 'Hybrid funds mix equity and debt to balance growth and stability.',
  debt: 'Debt funds focus on bonds and money market instruments and are generally used for stability, liquidity, or lower volatility.',
  elss: 'ELSS funds are equity-oriented tax-saving funds with a 3-year lock-in.',
  sif: 'SIFs can follow more flexible strategies than normal mutual funds and usually suit informed investors.',
};

const MARKET_NEWS = [
  {
    headline: 'Large caps remain steadier than broader equity pockets',
    summary: 'In this demo market snapshot, diversified large-cap exposure is holding up better than higher-volatility segments.',
  },
  {
    headline: 'Debt allocations are helping reduce portfolio swings',
    summary: 'Hybrid and short-duration debt categories are useful when investors want smoother movement with reasonable liquidity.',
  },
  {
    headline: 'SIP discipline still matters more than short-term noise',
    summary: 'For long-term goals, staying consistent with SIPs often matters more than trying to time every market move.',
  },
];

const DISTRIBUTORS = {
  delhi: [
    'Dhanada Advisor Desk - Connaught Place',
    'Dhanada Partner Advisor - South Delhi',
  ],
  mumbai: [
    'Dhanada Advisor Desk - Lower Parel',
    'Dhanada Partner Advisor - Andheri East',
  ],
  bengaluru: [
    'Dhanada Advisor Desk - Indiranagar',
    'Dhanada Partner Advisor - Whitefield',
  ],
  hyderabad: [
    'Dhanada Advisor Desk - Banjara Hills',
    'Dhanada Partner Advisor - Gachibowli',
  ],
  default: [
    'Dhanada Digital Advisor Desk',
    'Dhanada Phone Support Advisor',
  ],
};

function normalizeText(value) {
  return String(value || '').toLowerCase().trim();
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(value);
}

function findFund(query) {
  const text = normalizeText(query);
  return (
    FUNDS.find((fund) =>
      [fund.name.toLowerCase(), ...fund.aliases].some((alias) => text.includes(alias))
    ) || null
  );
}

function findFundMatches(query) {
  const text = normalizeText(query);
  return FUNDS.filter((fund) =>
    [fund.name.toLowerCase(), ...fund.aliases].some((alias) => text.includes(alias))
  );
}

function findAMC(query) {
  const text = normalizeText(query);
  return (
    AMC_DETAILS.find((amc) =>
      [amc.name.toLowerCase(), ...amc.aliases].some((alias) => text.includes(alias))
    ) || null
  );
}

function findCategory(query) {
  const text = normalizeText(query);
  return Object.keys(CATEGORY_GUIDES).find((category) => text.includes(category)) || null;
}

function findCity(query) {
  const text = normalizeText(query);
  return Object.keys(DISTRIBUTORS).find((city) => city !== 'default' && text.includes(city)) || 'default';
}

export function getFundDetails(query) {
  const fund = findFund(query);

  if (!fund) {
    return {
      status: 'missing',
      message:
        'I do not have that exact scheme in the demo data yet. I can still explain how to check category, NAV, risk, cost, and exit load.',
      availableFunds: FUNDS.map((item) => item.name),
    };
  }

  return {
    status: 'ok',
    fund,
    note: 'Demo scheme data for local testing.',
  };
}

export function getNAV(query) {
  const fund = findFund(query);

  if (!fund) {
    return {
      status: 'missing',
      message: 'Please share the scheme name. In this demo, I can show sample NAV data for the listed funds.',
      availableFunds: FUNDS.map((item) => item.name),
    };
  }

  return {
    status: 'ok',
    fundName: fund.name,
    nav: formatCurrency(fund.nav),
    asOf: DEMO_DATE,
    note: 'Demo NAV snapshot. Replace this method with a live API later.',
  };
}

export function getAMC(query) {
  const fund = findFund(query);
  const amc = findAMC(query) || (fund ? findAMC(fund.amc) : null);

  if (!amc) {
    return {
      status: 'missing',
      message: 'Please share the AMC name or fund name. I can explain the fund house and its strengths.',
      availableAMCs: AMC_DETAILS.map((item) => item.name),
    };
  }

  return {
    status: 'ok',
    amc,
  };
}

export function getRisk(query) {
  const fund = findFund(query);

  if (fund) {
    return {
      status: 'ok',
      mode: 'fund',
      fundName: fund.name,
      risk: fund.risk,
      summary: `${fund.name} sits in the ${fund.risk} risk band and is usually used by investors matching the category and time horizon.`,
    };
  }

  return {
    status: 'ok',
    mode: 'general',
    bands: [
      'Low: short duration and higher quality debt categories.',
      'Moderate: hybrid and balanced strategies.',
      'Moderately High to High: most diversified equity and tax-saving funds.',
    ],
  };
}

export function getCategory(query) {
  const fund = findFund(query);

  if (fund) {
    return {
      status: 'ok',
      category: fund.category,
      summary: `${fund.name} belongs to the ${fund.category} category.`,
    };
  }

  const category = findCategory(query);

  if (category) {
    return {
      status: 'ok',
      category,
      summary: CATEGORY_GUIDES[category],
    };
  }

  return {
    status: 'ok',
    categories: Object.keys(CATEGORY_GUIDES),
    summary:
      'Common categories are large cap, flexi cap, hybrid, debt, ELSS, and SIF. Each serves a different goal and risk level.',
  };
}

export function getPerformance(query) {
  const fund = findFund(query);

  if (!fund) {
    return {
      status: 'missing',
      message: 'Please share the scheme name. I can show sample 1Y, 3Y, and 5Y performance for the demo funds.',
      availableFunds: FUNDS.map((item) => item.name),
    };
  }

  return {
    status: 'ok',
    fundName: fund.name,
    performance: fund.performance,
    note: 'Sample performance data for local testing.',
  };
}

export function getMarketNews() {
  return {
    status: 'ok',
    asOf: DEMO_DATE,
    items: MARKET_NEWS,
    note: 'This is a demo market snapshot, not a live feed.',
  };
}

export function getDistributor(query) {
  const city = findCity(query);
  return {
    status: 'ok',
    city: city === 'default' ? 'your area' : city,
    options: DISTRIBUTORS[city],
  };
}

export function getInvestmentGuide(query) {
  const text = normalizeText(query);

  if (text.includes('tax')) {
    return {
      status: 'ok',
      topic: TOPIC_GUIDES.taxation.title,
      summary: TOPIC_GUIDES.taxation.summary,
      steps: [
        'Check whether the fund is equity-oriented, debt-oriented, or ELSS.',
        'Check holding period because tax treatment changes with duration.',
        'Match post-tax returns with your goal, not just pre-tax performance.',
      ],
    };
  }

  if (text.includes('kyc')) {
    return {
      status: 'ok',
      topic: TOPIC_GUIDES.kyc.title,
      summary: TOPIC_GUIDES.kyc.summary,
      steps: [
        'Keep PAN and Aadhaar ready.',
        'Complete identity and address verification.',
        'Use the verified profile for future investments.',
      ],
    };
  }

  if (text.includes('lumpsum')) {
    return {
      status: 'ok',
      topic: TOPIC_GUIDES.lumpsum.title,
      summary: TOPIC_GUIDES.lumpsum.summary,
      steps: [
        'Check your time horizon first.',
        'Avoid putting emergency cash into volatile funds.',
        'Consider phased entry if market swings make you uncomfortable.',
      ],
    };
  }

  return {
    status: 'ok',
    topic: TOPIC_GUIDES.sip.title,
    summary: TOPIC_GUIDES.sip.summary,
    steps: [
      'Choose a monthly amount you can continue comfortably.',
      'Pick a fund that matches your risk and goal.',
      'Review once or twice a year instead of reacting to every move.',
    ],
  };
}

export function getPlatformOverview() {
  return {
    status: 'ok',
    summary: TOPIC_GUIDES.dhanadaServices.summary,
    services: [
      'Fund comparison',
      'SIP and lumpsum planning',
      'Goal-based recommendations',
      'KYC support',
      'Advisor connection',
      'Portfolio review support',
    ],
  };
}

export function compareFunds(query) {
  const matches = findFundMatches(query);

  if (matches.length < 2) {
    return {
      status: 'needs_more_info',
      message: 'Please share two scheme names to compare.',
      availableFunds: FUNDS.map((item) => item.name),
    };
  }

  const [first, second] = matches.slice(0, 2);

  return {
    status: 'ok',
    funds: [first, second],
    summary:
      'Compare category fit first, then risk, cost, and consistency. A stronger past return alone is not enough.',
  };
}

export function getRecommendation(profile = {}) {
  const risk = normalizeText(profile.risk);
  const goal = normalizeText(profile.goal);
  const horizonYears = Number(profile.horizonYears || 0);
  const mode = normalizeText(profile.mode);

  const suggestions = [];
  const rationale = [];

  if (goal.includes('tax')) {
    suggestions.push(FUNDS.find((fund) => fund.name === 'Prism Tax Saver Fund'));
    rationale.push('ELSS can help if tax saving is one of your goals.');
  }

  if (risk.includes('conservative') || horizonYears > 0 && horizonYears <= 3) {
    suggestions.push(FUNDS.find((fund) => fund.name === 'Atlas Short Duration Debt Fund'));
    suggestions.push(FUNDS.find((fund) => fund.name === 'Cedar Balanced Advantage Fund'));
    rationale.push('Shorter or steadier goals usually need lower volatility than pure equity.');
  } else if (risk.includes('moderate') || risk.includes('balanced')) {
    suggestions.push(FUNDS.find((fund) => fund.name === 'Cedar Balanced Advantage Fund'));
    suggestions.push(FUNDS.find((fund) => fund.name === 'Horizon Bluechip Fund'));
    rationale.push('A balanced mix can pair smoother movement with long-term growth potential.');
  } else {
    suggestions.push(FUNDS.find((fund) => fund.name === 'Zenith Flexi Cap Fund'));
    suggestions.push(FUNDS.find((fund) => fund.name === 'Horizon Bluechip Fund'));
    rationale.push('Longer and growth-focused goals can usually take more equity exposure.');
  }

  const uniqueSuggestions = suggestions.filter(
    (fund, index) => fund && suggestions.findIndex((item) => item?.name === fund.name) === index
  );

  if (!uniqueSuggestions.length) {
    uniqueSuggestions.push(FUNDS[2], FUNDS[0]);
    rationale.push('These are sample starting points until you share your risk and horizon.');
  }

  return {
    status: 'ok',
    mode: mode || 'not specified',
    suggestions: uniqueSuggestions,
    rationale,
    summary:
      'These are sample starting points for the demo build, not personalized investment advice.',
  };
}

export function getGuideByKey(key) {
  return TOPIC_GUIDES[key] || null;
}

export const sampleFunds = FUNDS.map((fund) => fund.name);
