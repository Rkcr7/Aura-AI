// Real-Time Streaming Markdown Parser
// Integrates with existing MarkdownProcessor for incremental rendering

import { MarkdownProcessor } from './markdown-processor.js';

export class StreamingMarkdownParser {
    constructor() {
        // Use the existing comprehensive markdown processor
        this.markdownProcessor = new MarkdownProcessor();
        this.reset();
        
        // Simple patterns for detecting completable elements during streaming
        this.patterns = {
            // When to trigger re-processing
            headerComplete: /^#{1,6}\s+.*\n/,
            codeBlockBoundary: /^```/,
            listItem: /^(\s*)([-*+]|\d+\.)\s+/,
            paragraphBreak: /\n\s*\n/,
            inlineComplete: /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/
        };
        
        // Thinking content filter regex
        this.thinkingRegex = /<think\s*>[\s\S]*?<\/think\s*>/gi;
    }

    reset() {
        // Clear all state for new response
        this.buffer = '';
        this.lastProcessedContent = '';
        this.processedLength = 0;
        this.lastRenderedHTML = '';
        // Raw (unescaped) code-block bodies, keyed by block id, so the copy
        // button can read them from JS instead of being inlined into markup.
        this.codeBlockSources = new Map();
    }

    /**
     * Process a new chunk and return updated HTML
     * @param {string} chunk - New text chunk
     * @returns {string} - Complete HTML content
     */
    processChunk(chunk) {
        this.buffer += chunk;
        
        // Determine if we should re-process based on content changes
        const shouldProcess = this.shouldReprocess();
        
        if (shouldProcess) {
            return this.processBuffer();
        } else {
            // Return last rendered content + new raw content
            return this.getIncrementalHTML();
        }
    }

    /**
     * Determine if we should reprocess the entire buffer
     */
    shouldReprocess() {
        const newContent = this.buffer.slice(this.processedLength);
        
        // Reprocess if we detect completed markdown elements
        if (
            this.patterns.headerComplete.test(newContent) ||         // Complete header
            this.patterns.codeBlockBoundary.test(newContent) ||      // Code block boundary
            this.patterns.paragraphBreak.test(newContent) ||         // Paragraph break
            this.patterns.inlineComplete.test(newContent) ||         // Complete inline formatting
            newContent.includes('\n- ') ||                          // List item
            newContent.includes('\n* ') ||                          // List item
            newContent.includes('\n1. ') ||                         // Numbered list
            newContent.includes('**') ||                            // Bold formatting
            newContent.includes('`') ||                             // Code formatting
            newContent.includes('[') ||                             // Link start
            newContent.includes('](')                               // Link completion
        ) {
            return true;
        }
        
        // Also reprocess every 3-4 chunks to catch edge cases
        return (this.buffer.length - this.processedLength) > 150;
    }

    /**
     * Process the buffer using the existing MarkdownProcessor
     */
    processBuffer() {
        try {
            // Find the last complete section (avoid processing incomplete elements)
            const processableContent = this.getProcessableContent();
            
            if (processableContent === this.lastProcessedContent) {
                // No new processable content, return incremental
                return this.getIncrementalHTML();
            }
            
            // Process with existing markdown processor
            const blocks = this.markdownProcessor.parseContent(processableContent);
            let renderedHTML = '';
            
            // Generate HTML for each block
            blocks.forEach(block => {
                const blockHTML = this.markdownProcessor.generateHTML(block);
                if (blockHTML !== null) {
                    // Use generated HTML from markdown processor
                    renderedHTML += blockHTML;
                } else if (block.type === 'code') {
                    // Handle code blocks that return null
                    renderedHTML += this.generateCodeBlockHTML(block);
                }
            });
            
            // Update state
            this.lastProcessedContent = processableContent;
            this.processedLength = processableContent.length;
            this.lastRenderedHTML = renderedHTML;
            
            return this.getIncrementalHTML();
            
        } catch (error) {
            console.warn('🔍 Markdown processing error:', error);
            // Fallback to simple HTML escaping
            return this.getSimpleFallback();
        }
    }

    /**
     * Get content that's safe to process (avoid incomplete elements)
     */
    getProcessableContent() {
        let content = this.buffer;
        
        // Don't process if we're potentially in the middle of a code block
        const codeBlockMatches = content.match(/```/g);
        if (codeBlockMatches && codeBlockMatches.length % 2 === 1) {
            // Odd number of ``` means we're inside a code block
            const lastCodeBlock = content.lastIndexOf('```');
            content = content.substring(0, lastCodeBlock);
        }
        
        // Don't process incomplete inline formatting
        const lastAsterisk = content.lastIndexOf('**');
        const lastBacktick = content.lastIndexOf('`');
        const lastBracket = content.lastIndexOf('[');
        
        // If there's an opening marker without a close, truncate
        if (lastAsterisk > -1 && !content.slice(lastAsterisk + 2).includes('**')) {
            content = content.substring(0, lastAsterisk);
        }
        
        if (lastBacktick > -1 && !content.slice(lastBacktick + 1).includes('`')) {
            content = content.substring(0, lastBacktick);
        }
        
        if (lastBracket > -1 && !content.slice(lastBracket).includes('](')) {
            content = content.substring(0, lastBracket);
        }
        
        // Filter thinking content AFTER determining safe content boundaries
        content = this.filterThinkingContent(content);
        
        return content;
    }

    /**
     * Get incremental HTML (rendered + pending)
     */
    getIncrementalHTML() {
        const pendingContent = this.buffer.slice(this.processedLength);
        
        if (pendingContent.trim()) {
            // Filter thinking content from pending content
            const filteredPending = this.filterThinkingContent(pendingContent);
            if (filteredPending.trim()) {
                const escapedPending = this.escapeHtml(filteredPending);
                return this.lastRenderedHTML + `<span class="pending-text" style="margin:0;padding:0;">${escapedPending}</span>`;
            }
        }
        
        return this.lastRenderedHTML;
    }

    /**
     * Simple fallback when processing fails
     */
    getSimpleFallback() {
        const filteredBuffer = this.filterThinkingContent(this.buffer);
        return `<p class="markdown-paragraph" style="margin:0;padding:0;">${this.escapeHtml(filteredBuffer)}</p>`;
    }

    /**
     * Generate HTML for code blocks (when MarkdownProcessor returns null)
     */
    generateCodeBlockHTML(block) {
        const language = block.language || 'javascript';
        const content = this.escapeHtml(block.content);
        const blockId = `code-block-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        // Keep the raw body in JS rather than inlining it into an onclick handler.
        this.codeBlockSources.set(blockId, block.content);

        // Generate code block with proper padding and spacing
        const html = `<div class="code-block-container" data-block-id="${blockId}" style="margin:0.75rem 0!important;padding:0!important;max-width:100%!important;overflow-x:hidden!important;word-wrap:break-word!important;border-radius:6px!important;"><div class="code-block-header" style="padding:0.4rem 1.25rem!important;"><span class="code-language">${language}</span><button class="copy-button" type="button" title="Copy code">📋</button></div><pre class="code-block language-${language}" style="padding:1rem 1.25rem!important;margin:0!important;"><code class="language-${language}">${content}</code></pre></div>`;

        // Schedule syntax highlighting and copy-button wiring for this block
        setTimeout(() => {
            this.applySyntaxHighlighting(blockId);
            this.attachCopyHandler(blockId);
        }, 10);

        return html;
    }

    /**
     * Wire the copy button for a rendered code block.
     *
     * The handler closes over the raw source instead of being written into an
     * onclick attribute: the previous inline form interpolated model-generated
     * code into a JS template literal inside HTML, so any code containing a
     * backtick or ${...} broke the button and could execute arbitrary script.
     */
    attachCopyHandler(blockId) {
        try {
            const blockElement = document.querySelector(`[data-block-id="${blockId}"]`);
            if (!blockElement) return;

            const button = blockElement.querySelector('.copy-button');
            if (!button || button.dataset.copyBound === 'true') return;

            const source = this.codeBlockSources.get(blockId) || '';
            button.dataset.copyBound = 'true';
            button.addEventListener('click', async () => {
                try {
                    await navigator.clipboard.writeText(source);
                    button.textContent = '✅';
                } catch (err) {
                    console.warn('🔍 Copy failed:', err);
                    button.textContent = '❌';
                }
                setTimeout(() => { button.textContent = '📋'; }, 2000);
            });
        } catch (error) {
            console.warn('🔍 Copy button wiring error:', error);
        }
    }
    
    /**
     * Apply Prism.js syntax highlighting to a specific code block
     */
    applySyntaxHighlighting(blockId) {
        try {
            const blockElement = document.querySelector(`[data-block-id="${blockId}"]`);
            if (blockElement && window.Prism) {
                const codeElement = blockElement.querySelector('code');
                if (codeElement) {
                    window.Prism.highlightElement(codeElement);
                    console.log('🎨 Applied syntax highlighting to code block');
                }
            }
        } catch (error) {
            console.warn('🔍 Syntax highlighting error:', error);
        }
    }
    
    /**
     * Apply syntax highlighting to all code blocks in streaming content
     */
    highlightAllCodeBlocks() {
        try {
            if (window.Prism) {
                const codeBlocks = document.querySelectorAll('.code-block-container code[class*="language-"]');
                codeBlocks.forEach(codeElement => {
                    window.Prism.highlightElement(codeElement);
                });
                if (codeBlocks.length > 0) {
                    console.log(`🎨 Applied syntax highlighting to ${codeBlocks.length} code blocks`);
                }
            }
        } catch (error) {
            console.warn('🔍 Syntax highlighting error:', error);
        }
    }

    /**
     * Get the final rendered content (for when streaming completes)
     */
    finalize() {
        // Apply final thinking content filter to buffer
        this.buffer = this.filterThinkingContent(this.buffer);
        
        // Process the entire buffer one final time
        try {
            const blocks = this.markdownProcessor.parseContent(this.buffer);
            let finalHTML = '';
            
            // Generate HTML for each block using the full markdown processor
            blocks.forEach(block => {
                const blockHTML = this.markdownProcessor.generateHTML(block);
                if (blockHTML !== null) {
                    // Use generated HTML from markdown processor
                    finalHTML += blockHTML;
                } else if (block.type === 'code') {
                    // Handle code blocks that return null
                    finalHTML += this.generateCodeBlockHTML(block);
                }
            });
            
            // Apply syntax highlighting to all code blocks after finalization
            setTimeout(() => this.highlightAllCodeBlocks(), 50);
            
            return finalHTML;
            
        } catch (error) {
            console.warn('🔍 Final markdown processing error:', error);
            // Fallback to simple processing
            return `<p class="markdown-paragraph">${this.escapeHtml(this.buffer)}</p>`;
        }
    }

    /**
     * Filter thinking content from text
     * @param {string} content - Text content to filter
     * @returns {string} - Filtered content without thinking tags
     */
    filterThinkingContent(content) {
        if (!content || typeof content !== 'string') {
            return content;
        }
        
        const originalLength = content.length;
        
        // Remove content between <think> and </think> tags (case insensitive, multiline)
        // But preserve surrounding whitespace structure
        let filteredContent = content.replace(this.thinkingRegex, (match, offset, string) => {
            // Check if the thinking block is on its own line(s)
            const beforeMatch = string.substring(0, offset);
            const afterMatch = string.substring(offset + match.length);
            
            const beforeEndsWithNewline = beforeMatch.endsWith('\n') || beforeMatch.endsWith('\n\n');
            const afterStartsWithNewline = afterMatch.startsWith('\n') || afterMatch.startsWith('\n\n');
            
            // If the thinking block is on its own line, preserve one newline
            if (beforeEndsWithNewline && afterStartsWithNewline) {
                return '\n';
            }
            // If it's inline, just remove it
            return '';
        });
        
        // Only clean up excessive newlines (3 or more consecutive), preserve normal paragraph breaks
        filteredContent = filteredContent.replace(/\n{3,}/g, '\n\n');
        
        // Log if thinking content was filtered (only for significant changes to avoid spam)
        if (originalLength !== filteredContent.length && originalLength - filteredContent.length > 10) {
            console.log(`🧠 StreamingParser filtered thinking content: ${originalLength} → ${filteredContent.length} chars`);
        }
        
        return filteredContent;
    }

    escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
} 