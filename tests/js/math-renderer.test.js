import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import katex from 'katex';

import {
    extractMath,
    maskMath,
    findUnclosedDisplayMath,
    renderMathSegment,
    restoreMath
} from '../../web/js/math-renderer.js';

const texOf = (text) => extractMath(text).segments.map(s => [s.tex, s.display]);

describe('extractMath: delimiters', () => {
    test('$$...$$ is display math', () => {
        assert.deepEqual(texOf('a $$x^2$$ b'), [['x^2', true]]);
    });

    test('$$ spanning lines is one display segment', () => {
        assert.deepEqual(texOf('$$\n\\frac{a}{b}\n$$'), [['\\frac{a}{b}', true]]);
    });

    test('\\[...\\] is display math', () => {
        assert.deepEqual(texOf('\\[\nx = 1\n\\]'), [['x = 1', true]]);
    });

    test('\\(...\\) is inline math', () => {
        assert.deepEqual(texOf('so \\(a+b\\) holds'), [['a+b', false]]);
    });

    test('$...$ is inline math', () => {
        assert.deepEqual(texOf('Inline: $-X(12 - X) = -12X + X^2$'), [['-X(12 - X) = -12X + X^2', false]]);
    });

    test('single-character inline math', () => {
        assert.deepEqual(texOf('Substitute $T$ into $Y_d$'), [['T', false], ['Y_d', false]]);
    });

    test('several $$ blocks on one line stay separate', () => {
        assert.equal(extractMath('$$a$$ $$b$$ $$c$$').segments.length, 3);
    });

    test('text is replaced by placeholders', () => {
        assert.equal(extractMath('x $a$ y $$b$$ z').text, 'x __MATH_0__ y __MATH_1__ z');
    });
});

describe('extractMath: cases from the issue screenshots', () => {
    test('comparison operators inside inline math', () => {
        assert.deepEqual(texOf('(since $0 < b, t < 1$, the multiplier $> 1$).'), [
            ['0 < b, t < 1', false],
            ['> 1', false]
        ]);
    });

    test('backslash commands inside inline math', () => {
        assert.deepEqual(texOf('changes ($dx \\to 0$).'), [['dx \\to 0', false]]);
    });

    test('brackets inside display math', () => {
        assert.deepEqual(texOf('$$Y [1 - b(1 - t)] = C_0$$'), [['Y [1 - b(1 - t)] = C_0', true]]);
    });
});

describe('extractMath: things that are not math', () => {
    for (const text of [
        'It costs $5 and $10 in total.',
        'Between $5-$10 per month.',
        'Budget: $5 to $10',
        'Use $HOME and $PATH.',
        'Only one $ sign here.',
        '$ spaced $ is not math'
    ]) {
        test(JSON.stringify(text), () => {
            const { text: out, segments } = extractMath(text);
            assert.equal(segments.length, 0);
            assert.equal(out, text);
        });
    }

    test('$ inside inline code is left alone', () => {
        const input = 'Run `echo $x$` first';
        assert.deepEqual(extractMath(input), { text: input, segments: [] });
    });

    test('escaped \\$ becomes a literal dollar and opens nothing', () => {
        assert.deepEqual(extractMath('pay \\$5 and \\$10'), { text: 'pay $5 and $10', segments: [] });
    });

    test('$$ / $$$ price tiers do not swallow list items', () => {
        const input = '1. **Luigi** - Price: $$ - Great pasta.\n2. **Chez Paul** - Price: $$$ - French.\n3. Done.';
        assert.deepEqual(extractMath(input), { text: input, segments: [] });
    });

    test('a stray $$ never pairs across a blank line', () => {
        assert.deepEqual(texOf('Price: $$ cheap\n\nThe formula $$x^2$$ here'), [['x^2', true]]);
    });

    test('a stray $$ never pairs across a fenced code placeholder', () => {
        assert.deepEqual(texOf('PID is $$:\n__CODE_BLOCK_0__\nformula $$x$$'), [['x', true]]);
    });

    test('$ in link targets and URLs is not math', () => {
        for (const input of [
            '[Graph docs](https://graph.microsoft.com/v1.0/users?$select=id&$top=5)',
            'GET https://graph.microsoft.com/v1.0/users?$select=id&$top=5 then'
        ]) {
            assert.deepEqual(extractMath(input), { text: input, segments: [] });
        }
    });

    test('escaped backslash right before the closing $$', () => {
        assert.deepEqual(texOf('$$a = b \\\\$$ and the rest'), [['a = b \\\\', true]]);
    });

    test('empty and non-string input pass through', () => {
        assert.deepEqual(extractMath(''), { text: '', segments: [] });
        assert.deepEqual(extractMath(undefined), { text: undefined, segments: [] });
    });
});

describe('maskMath', () => {
    test('keeps length and blanks only the math', () => {
        const input = 'see [link]( $$Y [1 - b]$$ and **bold** $a*b$';
        const masked = maskMath(input);
        assert.equal(masked.length, input.length);
        assert.equal(masked.indexOf('[1'), -1);
        assert.equal(masked.includes('a*b'), false);
        assert.ok(masked.startsWith('see [link]( '));
        assert.ok(masked.includes('**bold**'));
    });
});

describe('findUnclosedDisplayMath', () => {
    test('returns -1 when every block is closed', () => {
        assert.equal(findUnclosedDisplayMath('a $$x$$ b \\[y\\] c'), -1);
    });

    test('finds an open $$', () => {
        const text = 'done $$x$$ then $$\\frac{a}{';
        assert.equal(findUnclosedDisplayMath(text), text.lastIndexOf('$$'));
    });

    test('finds an open \\[', () => {
        const text = 'start \\[ x = ';
        assert.equal(findUnclosedDisplayMath(text), text.indexOf('\\['));
    });

    test('ignores $$ inside fenced and inline code', () => {
        assert.equal(findUnclosedDisplayMath('```bash\necho $$\n```\nand `$$` too'), -1);
    });

    test('a blank line or code fence closes a stray opener', () => {
        assert.equal(findUnclosedDisplayMath('Price: $$ cheap\n\nMore text'), -1);
        assert.equal(findUnclosedDisplayMath('PID $$\n```bash\necho\n```\nafter'), -1);
    });

    test('agrees with extractMath on an escaped backslash before $$', () => {
        assert.equal(findUnclosedDisplayMath('$$a = b \\\\$$ and the rest'), -1);
    });

    test('$$$ is not an opener', () => {
        assert.equal(findUnclosedDisplayMath('Price: $$$ - French.'), -1);
    });
});

describe('renderMathSegment', () => {
    test('inline math renders with KaTeX', () => {
        const html = renderMathSegment({ tex: 'x^2', display: false, source: '$x^2$' }, katex);
        assert.match(html, /^<span class="md-math md-math-inline"><span class="katex">/);
    });

    test('display math renders in display mode', () => {
        const html = renderMathSegment({ tex: '\\Pi = 80X', display: true, source: '$$\\Pi = 80X$$' }, katex);
        assert.match(html, /md-math-display/);
        assert.match(html, /katex-display/);
    });

    test('invalid TeX renders an inline error instead of throwing', () => {
        const html = renderMathSegment({ tex: '\\frac{1}{', display: false, source: '$\\frac{1}{$' }, katex);
        assert.match(html, /katex-error/);
    });

    test('without KaTeX it falls back to the escaped original source', () => {
        const html = renderMathSegment({ tex: 'x < 5', display: false, source: '$x < 5$' }, null);
        assert.equal(html, '<span class="md-math md-math-raw">$x &lt; 5$</span>');
    });

    test('untrusted commands are not turned into links', () => {
        const html = renderMathSegment({ tex: '\\href{javascript:alert(1)}{x}', display: false, source: '' }, katex);
        assert.equal(html.includes('href="javascript'), false);
    });

    test('huge \\rule sizes are capped', () => {
        const html = renderMathSegment({ tex: '\\rule{5000em}{5000em}', display: false, source: '' }, katex);
        // The MathML annotation always echoes the TeX source; check the visible part
        const visible = html.slice(html.indexOf('katex-html'));
        assert.match(visible, /border-right-width:10em/);
        assert.equal(visible.includes('5000em'), false);
    });
});

describe('restoreMath', () => {
    test('replacement text is inserted literally ($& is not a pattern)', () => {
        const segments = [{ id: '__MATH_0__', tex: 'x', display: false, source: '$&' }];
        assert.equal(restoreMath('<p>__MATH_0__</p>', segments, null), '<p><span class="md-math md-math-raw">$&amp;</span></p>');
    });

    test('raw display fallback keeps the spaces around it', () => {
        const segments = [{ tex: 'x', display: true, source: '$$x$$' }];
        assert.equal(restoreMath('a __MATH_0__ b', segments, null), 'a <span class="md-math md-math-raw">$$x$$</span> b');
    });

    test('unknown placeholders are left as they are', () => {
        assert.equal(restoreMath('__MATH_7__', [{ tex: 'x', display: false, source: '$x$' }], null), '__MATH_7__');
    });
});
