import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import katex from 'katex';

import { MarkdownProcessor } from '../../web/js/markdown-processor.js';
import { StreamingMarkdownParser } from '../../web/js/streaming-markdown-parser.js';

// In the app KaTeX arrives as a global from the CDN <script>; mirror that here.
before(() => { globalThis.katex = katex; });
after(() => { delete globalThis.katex; });

// The streaming parser logs filtering/highlighting chatter; keep test output readable.
const quietConsole = () => {
    const original = console.log;
    console.log = () => {};
    return () => { console.log = original; };
};

const fixture = readFileSync(new URL('./fixtures/issue-6-math-response.md', import.meta.url), 'utf8');

const render = (text, config) => {
    const processor = new MarkdownProcessor(config);
    return processor.parseContent(text).map(block => processor.generateHTML(block) ?? '').join('');
};

const countMatches = (html, pattern) => (html.match(pattern) || []).length;

describe('MarkdownProcessor math', () => {
    test('issue example: block equation renders, no raw $$ left', () => {
        const html = render('Block equations: $$\\Pi = 80X - 2X^2 - XY - 3Y^2 + 100Y$$');
        assert.match(html, /katex-display/);
        assert.equal(html.includes('$$'), false);
    });

    test('issue example: inline equation renders', () => {
        const html = render('Inline: $-X(12 - X) = -12X + X^2$');
        assert.match(html, /md-math-inline/);
        assert.equal(html.includes('$-X'), false);
    });

    test('* inside math is not turned into italics', () => {
        const html = render('Product: $a * b * c$');
        assert.equal(html.includes('markdown-italic'), false);
    });

    test('< inside math reaches KaTeX unescaped', () => {
        const html = render('Bound: $x < 5$');
        assert.match(html, /<annotation encoding="application\/x-tex">x &lt; 5<\/annotation>/);
        assert.equal(html.includes('&amp;lt;'), false);
    });

    test('brackets inside math do not become links', () => {
        const html = render('$[a](b)$');
        assert.equal(html.includes('markdown-link'), false);
    });

    test('math in list items, headers and table cells', () => {
        const html = render('#### Derivative of $z = e^{x}$\n\n- $x_1$\n\n| a | b |\n|---|---|\n| $|x| < 1$ | 2 |');
        assert.match(html, /<h4[^>]*>Derivative of <span class="md-math/);
        assert.match(html, /<li[^>]*><span class="md-math/);
        assert.match(html, /<td class="table-cell"><span class="md-math/);
        // |x| inside math must not split the table row into extra cells
        assert.equal(countMatches(html, /<td /g), 2);
    });

    test('code keeps its dollars', () => {
        const html = render('Run `echo $x$` then:\n\n```bash\necho "$a$"\n```');
        assert.equal(html.includes('md-math'), false);
        assert.match(html, /<code class="inline-code">echo \$x\$<\/code>/);
    });

    test('$$ around a code block does not swallow it', () => {
        const processor = new MarkdownProcessor();
        const blocks = processor.parseContent('In bash, $$ is the PID:\n\n```bash\necho $$\n```\n\nAnd the formula $$x^2$$ here.');
        assert.ok(blocks.some(block => block.type === 'code' && block.content === 'echo $$'));
        const html = blocks.map(block => processor.generateHTML(block) ?? '').join('');
        assert.equal(countMatches(html, /md-math-display/g), 1);
        assert.equal(html.includes('katex-error'), false);
    });

    test('$ in a link URL keeps the link intact', () => {
        const html = render('[Graph docs](https://graph.microsoft.com/v1.0/users?$select=id&$top=5)');
        assert.equal(html, '<p class="markdown-paragraph"><a class="markdown-link" href="https://graph.microsoft.com/v1.0/users?$select=id&amp;$top=5" target="_blank" rel="noopener noreferrer">Graph docs</a></p>');
    });

    test('prices stay plain text', () => {
        const html = render('It costs $5 and $10.');
        assert.equal(html, '<p class="markdown-paragraph">It costs $5 and $10.</p>');
    });

    test('raw HTML inside math cannot inject markup', () => {
        const html = render('$<img src=x onerror=alert(1)>$');
        assert.equal(html.includes('<img'), false);
    });

    test('spaces beside display math are dropped, beside inline math kept', () => {
        // .streaming-text is white-space: pre-wrap, so a stray space between two
        // display blocks renders as an empty line
        const display = render('$$a$$ $$b$$');
        assert.equal(display.includes('</span> <span class="md-math'), false);
        const inline = render('x $a$ y');
        assert.match(inline, /^<p class="markdown-paragraph">x <span class="md-math md-math-inline">.*<\/span> y<\/p>$/);
    });

    test('enableMath: false keeps the old raw behaviour', () => {
        const html = render('$x$', { enableMath: false });
        assert.equal(html, '<p class="markdown-paragraph">$x$</p>');
    });

    test('without KaTeX loaded the source is shown as text', () => {
        delete globalThis.katex;
        try {
            const html = render('Bound: $x < 5$');
            assert.equal(html, '<p class="markdown-paragraph">Bound: <span class="md-math md-math-raw">$x &lt; 5$</span></p>');
        } finally {
            globalThis.katex = katex;
        }
    });

    test('screenshot fixture: every equation renders, nothing raw or broken', () => {
        const html = render(fixture);
        // Hand-counted from the fixture
        assert.equal(countMatches(html, /class="md-math md-math-inline"/g), 15);
        assert.equal(countMatches(html, /class="md-math md-math-display"/g), 14);
        assert.equal(html.includes('md-math-raw'), false);
        assert.equal(html.includes('katex-error'), false);
        assert.equal(html.includes('__MATH_'), false);
        assert.match(html, /prices like \$5 and \$10 stay plain text/);
        assert.match(html, /<td class="table-cell">\$5 to \$10<\/td>/);
    });
});

describe('StreamingMarkdownParser math', () => {
    test('fixture streamed in small chunks never shows a broken equation', () => {
        const restore = quietConsole();
        try {
            const parser = new StreamingMarkdownParser();
            for (let i = 0; i < fixture.length; i += 7) {
                const html = parser.processChunk(fixture.slice(i, i + 7));
                assert.equal(html.includes('katex-error'), false, `broken math after ${i + 7} chars`);
                assert.equal(html.includes('__MATH_'), false, `placeholder leaked after ${i + 7} chars`);
            }
            // Once everything has arrived nothing should still be held back as
            // raw text waiting for a closer
            assert.equal(parser.getProcessableContent(), fixture);
            // Element ids come from a per-processor counter, so ignore them
            const withoutIds = (html) => html.replace(/ id="[^"]*"/g, '');
            assert.equal(withoutIds(parser.finalize()), withoutIds(render(fixture)));
        } finally {
            restore();
        }
    });

    test('an open $$ is held back until it closes', () => {
        const parser = new StreamingMarkdownParser();
        parser.buffer = 'Intro text\n\n$$\\frac{a}{';
        assert.equal(parser.getProcessableContent(), 'Intro text\n\n');
    });

    test('brackets inside math do not hold back the rest of the response', () => {
        const parser = new StreamingMarkdownParser();
        parser.buffer = '$$Y [1 - b(1 - t)] = C$$ and the text after it';
        assert.equal(parser.getProcessableContent(), parser.buffer);
    });

    const processable = (buffer) => {
        const parser = new StreamingMarkdownParser();
        parser.buffer = buffer;
        return parser.getProcessableContent();
    };

    test('a real unclosed link is still held back', () => {
        assert.equal(processable('With $x$ see [the docs'), 'With $x$ see ');
        assert.equal(processable('see [docs]'), 'see ');
        assert.equal(processable('see [docs](https://exa'), 'see ');
    });

    test('text after a completed bold label is not held back', () => {
        // The old check (lastIndexOf('**') then "is there a ** after it?") was
        // always true, so everything after the last bold stayed raw until the end
        const buffer = '**Magnitude:** $\\frac{1}{1 - b}$ and the rest';
        assert.equal(processable(buffer), buffer);
    });

    test('an open bold is held back', () => {
        assert.equal(processable('Done. **Magnitu'), 'Done. ');
    });

    test('closed inline code is not held back, open inline code is', () => {
        assert.equal(processable('Run `ls` then $x$'), 'Run `ls` then $x$');
        assert.equal(processable('Run `ls -'), 'Run ');
    });

    test('brackets that are not links do not hold back the response', () => {
        assert.equal(processable('Use arr[0] then $x$ more'), 'Use arr[0] then $x$ more');
    });

    test('** inside fenced code does not count as bold', () => {
        const buffer = '```python\nx**2\n```\nafter $y$';
        assert.equal(processable(buffer), buffer);
    });

    test('math-looking text inside a code fence does not stall the stream', () => {
        for (const buffer of [
            "Strip brackets:\n\n```python\nclean = re.sub(r'[\\[\\]]', '', s)\n```\nThen \\[ x^2 \\] and the rest.",
            '```bash\necho $$\n```\nThen $$E=mc^2$$ done'
        ]) {
            assert.equal(processable(buffer), buffer);
        }
    });

    test('markers inside inline code do not stall the stream', () => {
        for (const buffer of ['Use `**kwargs` to pass options, see $x$', 'Type `[` to open a list']) {
            assert.equal(processable(buffer), buffer);
        }
    });

    test('escaped backslash before the closing $$ does not stall the stream', () => {
        const buffer = '$$a = b \\\\$$ and the rest';
        assert.equal(processable(buffer), buffer);
    });
});
