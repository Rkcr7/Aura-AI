// Math Renderer for Live Interview
// Finds LaTeX math in model output and renders it with KaTeX (loaded globally
// from the CDN in index.html). Kept free of DOM access so it runs under Node tests.

// Captures the spaces around a placeholder so display math can drop them
const MATH_PLACEHOLDER = /([ \t]*)__MATH_(\d+)__([ \t]*)/g;
const RENDER_CACHE_LIMIT = 500;

// Body of a $$, \[ or \( block: may span lines, but never a blank line or a
// fenced-code placeholder, so a stray `$$` (a price tier, bash's PID) can't
// swallow the paragraphs and code that follow it. Backslash pairs are taken
// whole so `\$` and `\\` never end the body early.
const BLOCK_BODY = String.raw`(?:\\[\s\S]|(?!\n[ \t]*\n|__CODE_BLOCK_)[^\\$])+?`;

// One left-to-right scan. Alternatives are tried in order at each position, so
// code, links and escaped dollars are consumed before they can open math.
//   1. `inline code`   -> left untouched ($ inside code is not math)
//   2. ](link target)  -> left untouched (OData-style ?$select=...&$top=...)
//   3. https://url     -> left untouched
//   4. \$              -> literal dollar sign
//   5. $$ ... $$       -> display math; $$$ is never a delimiter
//   6. \[ ... \]       -> display math
//   7. \( ... \)       -> inline math
//   8. $ ... $         -> inline math, Pandoc rules so prices stay text: no
//                         space just inside either delimiter, no newline, and
//                         the closing $ is not followed by a digit ("$5 and $10")
const MATH_TOKEN = new RegExp([
    '`[^`\\n]+`',
    String.raw`\]\([^)\s]*\)`,
    String.raw`https?:\/\/[^\s<>]+`,
    String.raw`\\\$`,
    String.raw`(?<!\$)\$\$(${BLOCK_BODY})\$\$(?!\$)`,
    String.raw`\\\[(${BLOCK_BODY})\\\]`,
    String.raw`\\\((${BLOCK_BODY})\\\)`,
    String.raw`(?<![\\$])\$(?![\s$])((?:\\[\s\S]|[^\\$\n])+?)(?<![\s\\])\$(?!\d)`
].join('|'), 'g');

// Tokens that decide whether a display block is still open while streaming.
// Mirrors MATH_TOKEN: backslash pairs are consumed whole, and a blank line or a
// code fence ends any open block because MATH_TOKEN would never match across it.
const DISPLAY_DELIMITER_TOKEN = /```[\s\S]*?```|`[^`\n]+`|\n[ \t]*\n|\\[[\]]|\\[\s\S]|(?<!\$)\$\$(?!\$)/g;

const KATEX_OPTIONS = Object.freeze({
    throwOnError: false, // bad TeX renders as red source text instead of throwing
    errorColor: '#ff8a80', // KaTeX's default #cc0000 is unreadable on the dark overlay
    strict: 'ignore',    // models mix unicode into math; don't spam the console
    trust: false,        // no \href, \url, \htmlClass etc. from model output
    maxSize: 10,         // cap \rule / \kern sizes (em): vision reads untrusted screen text
    output: 'htmlAndMathml'
});

const renderCache = new Map();

/**
 * Classify one MATH_TOKEN match.
 * @returns {{kind: 'skip'|'escaped'|'math', tex?: string, display?: boolean}}
 */
function classifyMatch(match, dollarDisplay, bracketDisplay, parenInline, dollarInline) {
    if (dollarDisplay !== undefined) return { kind: 'math', tex: dollarDisplay, display: true };
    if (bracketDisplay !== undefined) return { kind: 'math', tex: bracketDisplay, display: true };
    if (parenInline !== undefined) return { kind: 'math', tex: parenInline, display: false };
    if (dollarInline !== undefined) return { kind: 'math', tex: dollarInline, display: false };
    // Code, link targets and URLs pass through unchanged
    return { kind: match === '\\$' ? 'escaped' : 'skip' };
}

// Same-length blank that keeps newlines, so masked text keeps its line and
// paragraph structure
const blankOut = (text) => text.replace(/[^\n]/g, ' ');

/**
 * Replace every math span with a __MATH_n__ placeholder so the markdown
 * passes (HTML escaping, italics on `*`, tables on `|`, links on `[`) never
 * see the TeX source.
 * @param {string} text
 * @returns {{text: string, segments: Array<{id: string, tex: string, display: boolean, source: string}>}}
 */
export function extractMath(text) {
    if (!text || typeof text !== 'string') {
        return { text, segments: [] };
    }

    const segments = [];
    const replaced = text.replace(MATH_TOKEN, (match, ...groups) => {
        const token = classifyMatch(match, ...groups.slice(0, 4));
        if (token.kind === 'skip') return match;
        if (token.kind === 'escaped') return '$';

        const id = `__MATH_${segments.length}__`;
        segments.push({ id, tex: token.tex.trim(), display: token.display, source: match });
        return id;
    });

    return { text: replaced, segments };
}

/**
 * Same-length copy of `text` with every math span blanked out. Lets the
 * streaming parser look for unclosed markdown markers ([, **, `) without
 * tripping over brackets and asterisks that live inside equations.
 * @param {string} text
 * @returns {string}
 */
export function maskMath(text) {
    if (!text || typeof text !== 'string') return text;

    return text.replace(MATH_TOKEN, (match, ...groups) => {
        const token = classifyMatch(match, ...groups.slice(0, 4));
        return token.kind === 'math' ? blankOut(match) : match;
    });
}

/**
 * Same-length copy of `text` with fenced code blocks blanked out.
 * @param {string} text
 * @returns {string}
 */
export function maskFencedCode(text) {
    if (!text || typeof text !== 'string') return text;
    return text.replace(/```[\s\S]*?```/g, blankOut);
}

/**
 * Same-length copy of `text` with `inline code` spans blanked out.
 * @param {string} text
 * @returns {string}
 */
export function maskInlineCode(text) {
    if (!text || typeof text !== 'string') return text;
    return text.replace(/`[^`\n]*`/g, blankOut);
}

/**
 * Index of a display-math opener ($$ or \[) that has no closer yet, or -1.
 * Fenced and inline code are skipped so `echo $$` in a code block doesn't count.
 * @param {string} text
 * @returns {number}
 */
export function findUnclosedDisplayMath(text) {
    if (!text || typeof text !== 'string') return -1;

    let open = null;
    for (const match of text.matchAll(DISPLAY_DELIMITER_TOKEN)) {
        const token = match[0];
        if (token.startsWith('```') || token.startsWith('\n')) {
            open = null; // a stray opener before code or a blank line was never math
        } else if (token === '$$') {
            open = open?.delimiter === '$$' ? null : (open ?? { delimiter: '$$', index: match.index });
        } else if (token === '\\[') {
            open = open ?? { delimiter: '\\[', index: match.index };
        } else if (token === '\\]' && open?.delimiter === '\\[') {
            open = null;
        }
    }
    return open ? open.index : -1;
}

function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function resolveKatex(katexLib) {
    const lib = katexLib === undefined ? globalThis.katex : katexLib;
    return lib && typeof lib.renderToString === 'function' ? lib : null;
}

function rememberRender(key, html) {
    if (renderCache.size >= RENDER_CACHE_LIMIT) {
        renderCache.delete(renderCache.keys().next().value);
    }
    renderCache.set(key, html);
    return html;
}

/**
 * Render one segment to HTML. Falls back to the escaped original source
 * (delimiters included) when KaTeX isn't loaded, e.g. offline or CDN blocked.
 * @param {{tex: string, display: boolean, source: string}} segment
 * @param {object} [katexLib] - defaults to the global `katex` from the CDN
 * @returns {string}
 */
export function renderMathSegment(segment, katexLib) {
    const kind = segment.display ? 'display' : 'inline';
    const katex = resolveKatex(katexLib);

    if (katex) {
        const key = `${kind}:${segment.tex}`;
        const cached = renderCache.get(key);
        if (cached !== undefined) return cached;

        try {
            const html = katex.renderToString(segment.tex, { ...KATEX_OPTIONS, displayMode: segment.display });
            return rememberRender(key, `<span class="md-math md-math-${kind}">${html}</span>`);
        } catch (error) {
            console.warn('🧮 KaTeX render failed, showing source:', error);
        }
    }

    return `<span class="md-math md-math-raw">${escapeHtml(segment.source)}</span>`;
}

/**
 * Swap __MATH_n__ placeholders in an HTML string for rendered math.
 * @param {string} html
 * @param {Array} segments - from extractMath
 * @param {object} [katexLib]
 * @returns {string}
 */
export function restoreMath(html, segments, katexLib) {
    if (!html || typeof html !== 'string' || segments.length === 0) return html;

    // Function replacer: KaTeX's MathML annotation carries raw TeX, and a
    // string replacement would treat any `$&` or `$1` in it as a pattern.
    return html.replace(MATH_PLACEHOLDER, (placeholder, before, index, after) => {
        const segment = segments[Number(index)];
        if (!segment) return placeholder;

        const rendered = renderMathSegment(segment, katexLib);
        // Rendered display math is a block; spaces beside it would render as
        // blank lines under the overlay's `white-space: pre-wrap`. The raw
        // fallback is inline text, so it keeps them.
        const isBlock = rendered.startsWith('<span class="md-math md-math-display"');
        return isBlock ? rendered : `${before}${rendered}${after}`;
    });
}
