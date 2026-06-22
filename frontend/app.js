/**
 * Zomato AI Recommender — Main Application
 * Handles all UI interactions, state management, and API integration.
 */

// ============================================================
// STATE
// ============================================================

const state = {
  locations: [],
  cuisines: [],
  selectedLocation: '',
  selectedCuisine: '',
  selectedBudget: '',
  minRating: 0,
  extraPreferences: '',
  isLoading: false,
  lastQuery: null,
};

// ============================================================
// DOM REFS
// ============================================================

const DOM = {
  // Views
  inputView: document.getElementById('input-view'),
  loadingView: document.getElementById('loading-view'),
  resultsView: document.getElementById('results-view'),
  emptyView: document.getElementById('empty-view'),

  // Form
  form: document.getElementById('preference-form'),
  submitBtn: document.getElementById('submit-btn'),
  submitText: document.getElementById('submit-text'),
  submitSpinner: document.getElementById('submit-spinner'),

  // Location dropdown
  locationTrigger: document.getElementById('location-trigger'),
  locationDisplay: document.getElementById('location-display'),
  locationMenu: document.getElementById('location-menu'),
  locationSearch: document.getElementById('location-search'),
  locationOptions: document.getElementById('location-options'),
  locationValue: document.getElementById('location-value'),
  locationGroup: document.getElementById('location-group'),
  locationError: document.getElementById('location-error'),

  // Cuisine dropdown
  cuisineTrigger: document.getElementById('cuisine-trigger'),
  cuisineDisplay: document.getElementById('cuisine-display'),
  cuisineMenu: document.getElementById('cuisine-menu'),
  cuisineSearch: document.getElementById('cuisine-search'),
  cuisineOptions: document.getElementById('cuisine-options'),
  cuisineValue: document.getElementById('cuisine-value'),

  // Budget
  budgetControl: document.getElementById('budget-control'),
  budgetValue: document.getElementById('budget-value'),

  // Rating
  ratingSlider: document.getElementById('rating-slider'),
  ratingDisplay: document.getElementById('rating-display'),

  // Extra
  extraInput: document.getElementById('extra-input'),
  charCount: document.getElementById('char-count'),

  // Results
  queryPills: document.getElementById('query-pills'),
  cardsContainer: document.getElementById('cards-container'),

  // Buttons
  modifyBtn: document.getElementById('modify-btn'),
  retryBtn: document.getElementById('retry-btn'),
  newSearchBtn: document.getElementById('new-search-btn'),

  // Toast
  toastContainer: document.getElementById('toast-container'),

  // Navbar
  navbar: document.getElementById('navbar'),
};

// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener('DOMContentLoaded', init);

async function init() {
  setupEventListeners();
  setupScrollObserver();

  try {
    // Fetch meta data for dropdowns
    const [locations, cuisines] = await Promise.all([
      fetchLocations(),
      fetchCuisines(),
    ]);

    state.locations = locations || [];
    state.cuisines = cuisines || [];

    renderDropdownOptions('location', state.locations);
    renderDropdownOptions('cuisine', state.cuisines);
  } catch (err) {
    showToast('⚠️ ' + err.message);
  }
}

// ============================================================
// EVENT LISTENERS
// ============================================================

function setupEventListeners() {
  // Form submit
  DOM.form.addEventListener('submit', handleSubmit);

  // Location dropdown
  DOM.locationTrigger.addEventListener('click', () => toggleDropdown('location'));
  DOM.locationSearch.addEventListener('input', (e) => filterDropdown('location', e.target.value));

  // Cuisine dropdown
  DOM.cuisineTrigger.addEventListener('click', () => toggleDropdown('cuisine'));
  DOM.cuisineSearch.addEventListener('input', (e) => filterDropdown('cuisine', e.target.value));

  // Close dropdowns on outside click
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#location-dropdown')) closeDropdown('location');
    if (!e.target.closest('#cuisine-dropdown')) closeDropdown('cuisine');
  });

  // Budget segmented control
  DOM.budgetControl.querySelectorAll('.segment-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const isAlreadyActive = btn.classList.contains('active');
      DOM.budgetControl.querySelectorAll('.segment-btn').forEach(b => b.classList.remove('active'));
      if (!isAlreadyActive) {
        btn.classList.add('active');
        state.selectedBudget = btn.dataset.value;
      } else {
        state.selectedBudget = '';
      }
      DOM.budgetValue.value = state.selectedBudget;
    });
  });

  // Rating slider
  DOM.ratingSlider.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    state.minRating = val;
    DOM.ratingDisplay.textContent = val.toFixed(1);
    updateSliderTrack(e.target);
  });
  updateSliderTrack(DOM.ratingSlider);

  // Extra preferences
  DOM.extraInput.addEventListener('input', (e) => {
    state.extraPreferences = e.target.value;
    DOM.charCount.textContent = e.target.value.length;
  });

  // Suggestion chips
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      DOM.extraInput.value = chip.dataset.vibe;
      state.extraPreferences = chip.dataset.vibe;
      DOM.charCount.textContent = chip.dataset.vibe.length;
    });
  });

  // Modify / Retry / New Search buttons
  DOM.modifyBtn.addEventListener('click', showInputView);
  DOM.retryBtn.addEventListener('click', showInputView);
  DOM.newSearchBtn.addEventListener('click', showInputView);
}

// ============================================================
// DROPDOWN LOGIC
// ============================================================

function renderDropdownOptions(type, items) {
  const container = type === 'location' ? DOM.locationOptions : DOM.cuisineOptions;
  container.innerHTML = '';

  if (type === 'cuisine') {
    // Add "Any cuisine" option at top
    const anyOpt = document.createElement('div');
    anyOpt.className = 'dropdown-option';
    anyOpt.textContent = 'Any cuisine';
    anyOpt.addEventListener('click', () => selectDropdownItem(type, ''));
    container.appendChild(anyOpt);
  }

  items.forEach(item => {
    const opt = document.createElement('div');
    opt.className = 'dropdown-option';
    opt.textContent = item;
    opt.dataset.value = item;
    opt.addEventListener('click', () => selectDropdownItem(type, item));
    container.appendChild(opt);
  });
}

function toggleDropdown(type) {
  const menu = type === 'location' ? DOM.locationMenu : DOM.cuisineMenu;
  const trigger = type === 'location' ? DOM.locationTrigger : DOM.cuisineTrigger;
  const search = type === 'location' ? DOM.locationSearch : DOM.cuisineSearch;
  const isOpen = menu.classList.contains('visible');

  if (isOpen) {
    closeDropdown(type);
  } else {
    menu.classList.add('visible');
    trigger.classList.add('open');
    trigger.setAttribute('aria-expanded', 'true');
    search.value = '';
    filterDropdown(type, '');
    setTimeout(() => search.focus(), 50);
  }
}

function closeDropdown(type) {
  const menu = type === 'location' ? DOM.locationMenu : DOM.cuisineMenu;
  const trigger = type === 'location' ? DOM.locationTrigger : DOM.cuisineTrigger;
  menu.classList.remove('visible');
  trigger.classList.remove('open');
  trigger.setAttribute('aria-expanded', 'false');
}

function filterDropdown(type, query) {
  const container = type === 'location' ? DOM.locationOptions : DOM.cuisineOptions;
  const items = type === 'location' ? state.locations : state.cuisines;
  const q = query.toLowerCase().trim();
  const selectedVal = type === 'location' ? state.selectedLocation : state.selectedCuisine;

  container.innerHTML = '';

  if (type === 'cuisine') {
    const anyOpt = document.createElement('div');
    anyOpt.className = 'dropdown-option' + (selectedVal === '' ? ' selected' : '');
    anyOpt.textContent = 'Any cuisine';
    anyOpt.addEventListener('click', () => selectDropdownItem(type, ''));
    container.appendChild(anyOpt);
  }

  const filtered = q ? items.filter(item => item.toLowerCase().includes(q)) : items;

  filtered.forEach(item => {
    const opt = document.createElement('div');
    opt.className = 'dropdown-option' + (item === selectedVal ? ' selected' : '');

    // Highlight matching text
    if (q && item.toLowerCase().includes(q)) {
      const idx = item.toLowerCase().indexOf(q);
      opt.innerHTML =
        escapeHtml(item.substring(0, idx)) +
        '<span class="match">' + escapeHtml(item.substring(idx, idx + q.length)) + '</span>' +
        escapeHtml(item.substring(idx + q.length));
    } else {
      opt.textContent = item;
    }

    opt.dataset.value = item;
    opt.addEventListener('click', () => selectDropdownItem(type, item));
    container.appendChild(opt);
  });

  if (filtered.length === 0 && (type === 'location' || q)) {
    const noResult = document.createElement('div');
    noResult.className = 'dropdown-option';
    noResult.style.color = 'var(--outline)';
    noResult.style.cursor = 'default';
    noResult.textContent = 'No results found';
    container.appendChild(noResult);
  }
}

function selectDropdownItem(type, value) {
  if (type === 'location') {
    state.selectedLocation = value;
    DOM.locationValue.value = value;
    DOM.locationDisplay.textContent = value || 'Select a location...';
    DOM.locationDisplay.className = value ? '' : 'placeholder';
    DOM.locationGroup.classList.remove('has-error');
    DOM.locationError.classList.remove('visible');
  } else {
    state.selectedCuisine = value;
    DOM.cuisineValue.value = value;
    DOM.cuisineDisplay.textContent = value || 'Any cuisine';
    DOM.cuisineDisplay.className = value ? '' : 'placeholder';
  }
  closeDropdown(type);
}

// ============================================================
// SLIDER TRACK UPDATE
// ============================================================

function updateSliderTrack(slider) {
  const min = parseFloat(slider.min);
  const max = parseFloat(slider.max);
  const val = parseFloat(slider.value);
  const percent = ((val - min) / (max - min)) * 100;
  slider.style.background = `linear-gradient(90deg, var(--primary) 0%, var(--primary) ${percent}%, rgba(255, 255, 255, 0.08) ${percent}%, rgba(255, 255, 255, 0.08) 100%)`;
}

// ============================================================
// FORM SUBMISSION
// ============================================================

async function handleSubmit(e) {
  e.preventDefault();

  // Validate location
  if (!state.selectedLocation) {
    DOM.locationGroup.classList.add('has-error');
    DOM.locationError.classList.add('visible');
    DOM.locationTrigger.focus();
    return;
  }

  // Build preferences
  const preferences = {
    location: state.selectedLocation,
  };
  if (state.selectedCuisine) preferences.cuisine = state.selectedCuisine;
  if (state.selectedBudget) preferences.budget = state.selectedBudget;
  if (state.minRating > 0) preferences.min_rating = state.minRating;
  if (state.extraPreferences.trim()) preferences.extra_preferences = state.extraPreferences.trim();

  state.lastQuery = preferences;

  // Show loading
  showLoadingView();

  try {
    const result = await fetchRecommendations(preferences);

    if (!result.recommendations || result.recommendations.length === 0) {
      showEmptyView();
    } else {
      showResultsView(result);
    }
  } catch (err) {
    showToast('⚠️ ' + err.message);
    showInputView();
  }
}

// ============================================================
// VIEW MANAGEMENT
// ============================================================

function showInputView() {
  DOM.inputView.style.display = '';
  DOM.inputView.classList.remove('view-hidden');
  DOM.loadingView.classList.remove('visible');
  DOM.resultsView.classList.remove('visible');
  DOM.emptyView.classList.remove('visible');

  // Re-enable submit
  setSubmitLoading(false);

  // Re-animate hero and form
  const hero = DOM.inputView.querySelector('.hero');
  const formCard = DOM.inputView.querySelector('.form-card');
  const chips = DOM.inputView.querySelector('.suggestion-chips');
  [hero, formCard, chips].forEach(el => {
    if (el) {
      el.style.animation = 'none';
      el.offsetHeight; // force reflow
      el.style.animation = '';
    }
  });

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showLoadingView() {
  DOM.inputView.style.display = 'none';
  DOM.emptyView.classList.remove('visible');
  DOM.resultsView.classList.remove('visible');
  DOM.loadingView.classList.add('visible');
  setSubmitLoading(true);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showResultsView(result) {
  DOM.loadingView.classList.remove('visible');
  DOM.emptyView.classList.remove('visible');
  DOM.resultsView.classList.add('visible');
  setSubmitLoading(false);

  renderQueryPills(result.query_info);
  renderCards(result.recommendations);

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showEmptyView() {
  DOM.loadingView.classList.remove('visible');
  DOM.resultsView.classList.remove('visible');
  DOM.emptyView.classList.add('visible');
  setSubmitLoading(false);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function setSubmitLoading(loading) {
  state.isLoading = loading;
  DOM.submitBtn.disabled = loading;
  DOM.submitText.textContent = loading ? '✨ AI is thinking…' : '🔍 Find My Perfect Restaurant';
  DOM.submitSpinner.style.display = loading ? 'block' : 'none';
}

// ============================================================
// RENDER RESULTS
// ============================================================

function renderQueryPills(queryInfo) {
  DOM.queryPills.innerHTML = '';

  if (queryInfo.location) {
    DOM.queryPills.appendChild(createPill('📍', queryInfo.location));
  }
  if (queryInfo.cuisine) {
    DOM.queryPills.appendChild(createPill('🍽️', queryInfo.cuisine));
  }
  if (queryInfo.budget) {
    DOM.queryPills.appendChild(createPill('💰', capitalize(queryInfo.budget)));
  }
  if (queryInfo.min_rating && queryInfo.min_rating > 0) {
    DOM.queryPills.appendChild(createPill('⭐', queryInfo.min_rating + '+'));
  }
  if (queryInfo.extra_preferences) {
    DOM.queryPills.appendChild(createPill('✨', queryInfo.extra_preferences));
  }

  // Reset animation
  DOM.queryPills.style.animation = 'none';
  DOM.queryPills.offsetHeight;
  DOM.queryPills.style.animation = '';
}

function createPill(emoji, text) {
  const pill = document.createElement('span');
  pill.className = 'query-pill';
  pill.innerHTML = `<span class="emoji">${emoji}</span> ${escapeHtml(text)}`;
  return pill;
}

function renderCards(recommendations) {
  DOM.cardsContainer.innerHTML = '';

  recommendations.forEach((rec, idx) => {
    const card = document.createElement('div');
    card.className = 'rec-card glass';
    card.style.animationDelay = `${idx * 150}ms`;

    const rank = rec.rank || idx + 1;
    const rankClass = rank <= 3 ? `rank-${rank}` : 'rank-3';

    const ratingVal = rec.rate_float || rec.rate || '—';
    const votes = rec.votes ? `(${formatNumber(rec.votes)} votes)` : '';
    const cost = rec.approx_cost ? `₹${rec.approx_cost} for two` : '';
    const cuisines = rec.cuisines || '';
    const restType = rec.rest_type || '';
    const explanation = rec.ai_explanation || '';
    const address = rec.address || rec.location || '';

    card.innerHTML = `
      <div class="card-top">
        <div class="rank-badge ${rankClass}">#${rank}</div>
        ${rank === 1 ? '<span class="top-rated-badge">Top Rated</span>' : ''}
      </div>
      <div class="restaurant-name">${escapeHtml(rec.name)}</div>
      <div class="card-tags">
        ${cuisines ? `<span class="tag">${escapeHtml(cuisines)}</span>` : ''}
        ${restType ? `<span class="tag">${escapeHtml(restType)}</span>` : ''}
        ${cost ? `<span class="tag cost">${escapeHtml(cost)}</span>` : ''}
      </div>
      <div class="card-rating">
        <span class="rating-stars">⭐</span>
        <span class="rating-number">${ratingVal}</span>
        ${votes ? `<span class="rating-votes">${votes}</span>` : ''}
      </div>
      ${explanation ? `
        <div class="ai-section">
          <div class="ai-label">🤖 AI's Take</div>
          <div class="ai-explanation">${escapeHtml(explanation)}</div>
        </div>
      ` : ''}
      ${address ? `
        <div class="card-address">
          <span>📍</span>
          <span>${escapeHtml(address)}</span>
        </div>
      ` : ''}
    `;

    DOM.cardsContainer.appendChild(card);

    // Staggered animation
    setTimeout(() => {
      card.classList.add('animate-in');
    }, idx * 150);
  });
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>⚠️</span><span>${escapeHtml(message)}</span>`;
  DOM.toastContainer.appendChild(toast);

  toast.addEventListener('click', () => dismissToast(toast));

  setTimeout(() => dismissToast(toast), 5000);
}

function dismissToast(toast) {
  if (toast.classList.contains('fade-out')) return;
  toast.classList.add('fade-out');
  setTimeout(() => toast.remove(), 300);
}

// ============================================================
// NAVBAR SCROLL EFFECT
// ============================================================

function setupScrollObserver() {
  window.addEventListener('scroll', () => {
    if (window.scrollY > 20) {
      DOM.navbar.classList.add('scrolled');
    } else {
      DOM.navbar.classList.remove('scrolled');
    }
  });
}

// ============================================================
// UTILITIES
// ============================================================

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatNumber(num) {
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
  }
  return num.toString();
}
