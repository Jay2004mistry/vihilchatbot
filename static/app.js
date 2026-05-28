document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const chatForm = document.getElementById("chatForm");
    const userInput = document.getElementById("userInput");
    const chatMessages = document.getElementById("chatMessages");
    const recrawlBtn = document.getElementById("recrawlBtn");
    const scrapeOverlay = document.getElementById("scrapeOverlay");
    const tabContent = document.getElementById("tabContent");
    const tabButtons = document.querySelectorAll(".tab-btn");
    const micBtn = document.getElementById("micBtn");

    let knowledgeBase = null;
    let currentTab = "services";

    // 1. Initial Data Fetching
    async function fetchKnowledgeBase() {
        try {
            const res = await fetch("/api/data");
            if (res.ok) {
                knowledgeBase = await res.json();
                renderTabContent();
            } else {
                tabContent.innerHTML = `<div class="loading-spinner" style="color: #ef4444;">Failed to fetch database. Please click 'Sync Website'.</div>`;
            }
        } catch (err) {
            console.error("Error fetching knowledge base:", err);
            tabContent.innerHTML = `<div class="loading-spinner" style="color: #ef4444;">Error connecting to API server.</div>`;
        }
    }

    // 2. Tab Navigation & Rendering
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            tabButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentTab = btn.getAttribute("data-tab");
            renderTabContent();
        });
    });

    function renderTabContent() {
        if (!knowledgeBase || Object.keys(knowledgeBase).length === 0) {
            tabContent.innerHTML = `<div class="loading-spinner">No data loaded. Please trigger website sync.</div>`;
            return;
        }

        let html = "";

        if (currentTab === "services") {
            const services = knowledgeBase.services || [];
            const whatWeDo = knowledgeBase.what_we_do || [];

            html += `<h3 style="font-family: 'Outfit'; font-size: 1rem; margin-bottom: 12px; border-bottom: 1px solid var(--border-color); padding-bottom: 6px;">Core Development Services</h3>`;
            if (services.length > 0) {
                services.forEach(s => {
                    html += `
                        <div class="kb-card">
                            <h3>${s.title}</h3>
                            <p>${s.desc1}</p>
                        </div>
                    `;
                });
            } else {
                html += `<p style="color: var(--text-secondary); margin-bottom: 20px;">No core services parsed.</p>`;
            }

            html += `<h3 style="font-family: 'Outfit'; font-size: 1rem; margin-top: 24px; margin-bottom: 12px; border-bottom: 1px solid var(--border-color); padding-bottom: 6px;">Capabilities &amp; Solutions</h3>`;
            if (whatWeDo.length > 0) {
                whatWeDo.forEach(w => {
                    html += `
                        <div class="kb-card">
                            <h3>${w.name}</h3>
                            <p>${w.desc}</p>
                        </div>
                    `;
                });
            } else {
                html += `<p style="color: var(--text-secondary);">No capability items parsed.</p>`;
            }
        }

        else if (currentTab === "team") {
            const team = knowledgeBase.team || [];
            if (team.length > 0) {
                team.forEach(m => {
                    // Extract initials
                    const initials = m.name.split(" ").map(n => n[0]).join("").toUpperCase().substring(0, 2);
                    html += `
                        <div class="team-item">
                            <div class="team-avatar">${initials}</div>
                            <div class="team-details">
                                <h4>${m.name}</h4>
                                <p style="color: var(--secondary); font-weight: 500; font-size: 0.76rem;">${m.position.replace(/\(|\)/g, "").trim()}</p>
                                <p style="color: var(--text-secondary); font-size: 0.78rem; margin-top: 3px; line-height: 1.3;">${m.desc}</p>
                            </div>
                        </div>
                    `;
                });
            } else {
                html += `<p style="color: var(--text-secondary);">No team members found.</p>`;
            }
        }

        else if (currentTab === "faqs") {
            const faqs = knowledgeBase.faqs || [];
            if (faqs.length > 0) {
                faqs.forEach(f => {
                    html += `
                        <div class="kb-card">
                            <h3>Q: ${f.question}</h3>
                            <p><strong>A:</strong> ${f.answer}</p>
                        </div>
                    `;
                });
            } else {
                html += `<p style="color: var(--text-secondary);">No FAQs found.</p>`;
            }
        }

        else if (currentTab === "contact") {
            const company = knowledgeBase.company || {};
            const contact = company.contact || {};
            const stats = company.statistics || [];
            const vision = company.vision || {};

            // Render stats
            html += `<h3 style="font-family: 'Outfit'; font-size: 1rem; margin-bottom: 12px; border-bottom: 1px solid var(--border-color); padding-bottom: 6px;">Company Statistics</h3>`;
            if (stats.length > 0) {
                html += `<div class="stats-grid">`;
                stats.forEach(s => {
                    html += `
                        <div class="stat-box">
                            <div class="stat-num">${s.name}</div>
                            <div class="stat-name">${s.content}</div>
                        </div>
                    `;
                });
                html += `</div>`;
            }

            // Render vision
            if (vision && vision.description) {
                html += `
                    <div class="kb-card" style="margin-bottom: 24px;">
                        <h3>${vision.area || "Vision of our Company"}</h3>
                        <p>${vision.description}</p>
                    </div>
                `;
            }

            // Render Contact info
            html += `<h3 style="font-family: 'Outfit'; font-size: 1rem; margin-bottom: 12px; border-bottom: 1px solid var(--border-color); padding-bottom: 6px;">Contact Information</h3>`;
            html += `
                <div class="contact-section-pane">
                    <div class="contact-item">
                        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                        <p><strong>Address:</strong><br>${contact.address || "Nadiad, Gujarat, India."}</p>
                    </div>
                    <div class="contact-item">
                        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                        <p><strong>Email:</strong><br><a href="mailto:${contact.email}" style="color: var(--secondary); text-decoration: none;">${contact.email || "vihil3010@gmail.com"}</a></p>
                    </div>
                    <div class="contact-item">
                        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 5a2 2 0 012-2h3.28a1 1 0 01.94.725l.548 2.2a1 1 0 01-.321.988l-1.305.98a10.582 10.582 0 004.872 4.872l.98-1.305a1 1 0 01.988-.321l2.2.548a1 1 0 01.725.94V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
                        <p><strong>Phone:</strong><br>${contact.phone || "+91 7016421339"}</p>
                    </div>
                </div>
            `;

            // Socials
            if (contact.social_links) {
                html += `<div class="social-links" style="margin-top: 15px;">`;
                if (contact.social_links.facebook) {
                    html += `<a href="${contact.social_links.facebook}" target="_blank" class="social-link" title="Facebook"><svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg></a>`;
                }
                if (contact.social_links.instagram) {
                    html += `<a href="${contact.social_links.instagram}" target="_blank" class="social-link" title="Instagram"><svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.051.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg></a>`;
                }
                if (contact.social_links.twitter) {
                    html += `<a href="${contact.social_links.twitter}" target="_blank" class="social-link" title="Twitter"><svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/></svg></a>`;
                }
                if (contact.social_links.linkedin) {
                    html += `<a href="${contact.social_links.linkedin}" target="_blank" class="social-link" title="LinkedIn"><svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg></a>`;
                }
                html += `</div>`;
            }
        }

        tabContent.innerHTML = html;
    }

    // 3. Send Message / Query API
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;

        // Clear input
        userInput.value = "";

        // Append User Message to Log
        appendMessage(text, "user-message");

        // Append Typing Indicator
        const typingIndicator = appendTypingIndicator();
        scrollToBottom();

        try {
            const response = await fetch("/api/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: text })
            });

            // Remove Typing Indicator
            typingIndicator.remove();

            if (response.ok) {
                const data = await response.json();
                appendMessage(data.answer, "bot-message");
                speakText(data.answer);
            } else {
                appendMessage("Error generating answer. Please try again.", "bot-message");
                speakText("Error generating answer. Please try again.");
            }
        } catch (err) {
            typingIndicator.remove();
            console.error("Query Error:", err);
            appendMessage("Failed to communicate with AI server. Please check connection.", "bot-message");
        }
        scrollToBottom();
    });

    function appendMessage(text, className) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${className}`;

        // Format text with paragraph breaks
        const formattedText = text.replace(/\n/g, "<br>");

        msgDiv.innerHTML = `
            <div class="message-content">${formattedText}</div>
            <div class="message-time">Just now</div>
        `;
        chatMessages.appendChild(msgDiv);
    }

    function appendTypingIndicator() {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message bot-message typing-indicator-msg";
        msgDiv.innerHTML = `
            <div class="message-content">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        chatMessages.appendChild(msgDiv);
        return msgDiv;
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // 4. Sync/Recrawl Button Click
    recrawlBtn.addEventListener("click", async () => {
        // Show scrape overlay spinner
        scrapeOverlay.classList.add("active");

        try {
            const res = await fetch("/api/scrape", {
                method: "POST"
            });

            if (res.ok) {
                const result = await res.json();
                console.log(result.message);

                // Fetch fresh database contents
                await fetchKnowledgeBase();

                // Add system message
                appendMessage("Website content has been successfully crawled and updated in real-time!", "bot-message");
            } else {
                alert("Failed to crawl website. Backend error.");
            }
        } catch (err) {
            console.error("Crawl error:", err);
            alert("Error triggering crawl. Please make sure FastAPI app is running.");
        } finally {
            // Hide overlay
            scrapeOverlay.classList.remove("active");
            scrollToBottom();
        }
    });

    // 5. Speech Synthesis (Text-to-Speech)
    function speakText(text) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();

            // Remove markdown or special characters before speaking
            const cleanText = text.replace(/[*_#]/g, '').replace(/<[^>]+>/g, '');
            const utterance = new SpeechSynthesisUtterance(cleanText);

            // Basic heuristic to pick a language tag if supported
            if (/[\u0A80-\u0AFF]/.test(text)) {
                utterance.lang = 'gu-IN'; // Gujarati
            } else if (/[\u0900-\u097F]/.test(text)) {
                utterance.lang = 'hi-IN'; // Hindi
            } else {
                utterance.lang = 'en-US'; // Default English
            }

            window.speechSynthesis.speak(utterance);
        }
    }

    // 6. Speech Recognition (Voice Input)
    if (micBtn) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            const recognition = new SpeechRecognition();
            recognition.continuous = false;
            // Provide hint to support mixed languages or auto-detect if possible. 
            // Often we leave lang empty or default, or could set to something specific, but let's allow the browser default.
            recognition.interimResults = false;

            recognition.onstart = function () {
                micBtn.style.color = "#ef4444"; // Red to indicate recording
            };

            recognition.onresult = function (event) {
                const transcript = event.results[0][0].transcript;
                userInput.value = transcript;
                micBtn.style.color = "var(--text-secondary)";
                // Auto-submit form
                chatForm.dispatchEvent(new Event("submit"));
            };

            recognition.onerror = function (event) {
                console.error("Speech recognition error", event.error);
                micBtn.style.color = "var(--text-secondary)";
            };

            recognition.onend = function () {
                micBtn.style.color = "var(--text-secondary)";
            };

            micBtn.addEventListener("click", () => {
                // Cancel any ongoing speech when user starts talking
                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                }
                recognition.start();
            });
        } else {
            micBtn.style.display = "none";
            console.warn("Speech Recognition API not supported in this browser.");
        }
    }

    // Run Initial fetch
    fetchKnowledgeBase();
});
