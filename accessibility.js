// Lightweight accessibility controls without eval/unsafe code
(() => {
    const prefKey = 'a11yPreferences';
    const html = document.documentElement;
    const defaults = {
        large: false,
        contrast: false,
        links: false,
        motion: false
    };

    const loadPrefs = () => {
        try {
            const stored = localStorage.getItem(prefKey);
            return stored ? { ...defaults, ...JSON.parse(stored) } : { ...defaults };
        } catch (_) {
            return { ...defaults };
        }
    };

    const savePrefs = (prefs) => {
        try {
            localStorage.setItem(prefKey, JSON.stringify(prefs));
        } catch (_) {
            /* ignore storage failures */
        }
    };

    const state = loadPrefs();

    const applyState = (buttons) => {
        html.classList.toggle('a11y-large-text', state.large);
        html.classList.toggle('a11y-high-contrast', state.contrast);
        html.classList.toggle('a11y-highlight-links', state.links);
        html.classList.toggle('a11y-reduce-motion', state.motion);

        buttons.forEach((btn) => {
            const action = btn.dataset.action;
            if (action === 'reset') return;
            const active = Boolean(state[action]);
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
    };

    const buildWidget = () => {
        const widget = document.createElement('div');
        widget.className = 'a11y-widget';

        const launcher = document.createElement('button');
        launcher.type = 'button';
        launcher.className = 'a11y-launcher';
        launcher.setAttribute('aria-expanded', 'false');
        launcher.setAttribute('aria-controls', 'a11y-panel');
        launcher.setAttribute('aria-label', 'אפשרויות נגישות');
        launcher.innerHTML = `
            <i class="fas fa-universal-access" aria-hidden="true"></i>
            <span>אפשרויות נגישות</span>
        `;

        const panel = document.createElement('div');
        panel.className = 'a11y-panel';
        panel.id = 'a11y-panel';
        panel.setAttribute('role', 'dialog');
        panel.setAttribute('aria-label', 'אפשרויות נגישות');
        panel.hidden = true;
        panel.innerHTML = `
            <p class="a11y-panel-title">התאמות נגישות</p>
            <div class="a11y-actions" role="group" aria-label="התאמות נגישות">
                <button type="button" data-action="large">הגדלת טקסט</button>
                <button type="button" data-action="contrast">ניגודיות גבוהה</button>
                <button type="button" data-action="links">הדגשת קישורים</button>
                <button type="button" data-action="motion">צמצום אנימציות</button>
                <button type="button" data-action="reset" class="a11y-reset">איפוס</button>
            </div>
            <p class="a11y-note">ההגדרות נשמרות לשימוש הבא שלך.</p>
        `;

        widget.appendChild(launcher);
        widget.appendChild(panel);
        document.body.appendChild(widget);

        const actionButtons = panel.querySelectorAll('[data-action]');

        const closePanel = () => {
            panel.hidden = true;
            launcher.setAttribute('aria-expanded', 'false');
        };

        const togglePanel = () => {
            const isOpen = panel.hidden === false;
            panel.hidden = isOpen;
            launcher.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
            if (!isOpen) {
                panel.querySelector('[data-action]')?.focus();
            }
        };

        launcher.addEventListener('click', togglePanel);

        actionButtons.forEach((btn) => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                if (action === 'reset') {
                    Object.keys(state).forEach((key) => (state[key] = false));
                } else {
                    state[action] = !state[action];
                }
                applyState(actionButtons);
                savePrefs(state);
            });
        });

        document.addEventListener('click', (event) => {
            if (panel.hidden) return;
            if (!widget.contains(event.target)) {
                closePanel();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && panel.hidden === false) {
                closePanel();
                launcher.focus();
            }
        });

        applyState(actionButtons);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', buildWidget);
    } else {
        buildWidget();
    }
})();
