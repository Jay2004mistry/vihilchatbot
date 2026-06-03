document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chatForm");
    const userInput = document.getElementById("userInput");
    const chatMessages = document.getElementById("chatMessages");

    const micBtn = document.getElementById("micBtn");
    const langSelect = document.getElementById("langSelect");
    const topbarTime = document.getElementById("topbarTime");
    const muteBtn = document.getElementById("muteBtn");
    const muteIcon = document.getElementById("muteIcon");
    const clearBtn = document.getElementById("clearBtn");
    const modeButtons = document.querySelectorAll(".mode-btn");
    
    // Floating Button Elements
    const chatFab = document.getElementById("chatFab");
    const chatContainer = document.getElementById("chatContainer");
    const closeChatBtn = document.getElementById("closeChatBtn");

    if (chatFab && chatContainer) {
        chatFab.addEventListener("click", () => {
            chatContainer.classList.remove("hidden");
            chatFab.classList.add("hidden");
            // Auto-focus input when opened
            setTimeout(() => userInput.focus(), 300);
        });
    }

    if (closeChatBtn && chatContainer && chatFab) {
        closeChatBtn.addEventListener("click", () => {
            chatContainer.classList.add("hidden");
            chatFab.classList.remove("hidden");
        });
    }

    let isMuted = false;
    let currentPlayingAudio = null;
    let currentMode = "type";
    let recognition = null;
    let isListening = false;
    let micPermissionDenied = false;


    function stopAudio() {
        if (currentPlayingAudio) {
            currentPlayingAudio.pause();
            currentPlayingAudio.currentTime = 0;
            currentPlayingAudio = null;
        }
        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
        }
    }

    function setMuted(nextMuted) {
        isMuted = nextMuted;
        if (muteIcon) {
            muteIcon.innerHTML = isMuted
                ? `<path d="M6.717 3.55A.5.5 0 0 1 7 4v8a.5.5 0 0 1-.812.39L3.825 10.5H1.5A.5.5 0 0 1 1 10V6a.5.5 0 0 1 .5-.5h2.325l2.363-1.89a.5.5 0 0 1 .529-.06zm7.137 2.096a.5.5 0 0 1 0 .708L12.207 8l1.647 1.646a.5.5 0 0 1-.708.708L11.5 8.707l-1.646 1.647a.5.5 0 0 1-.708-.708L10.793 8 9.146 6.354a.5.5 0 1 1 .708-.708L11.5 7.293l1.646-1.647a.5.5 0 0 1 .708 0z"/>`
                : `<path d="M11.536 14.01A8.47 8.47 0 0 0 14.026 8a8.47 8.47 0 0 0-2.49-6.01l-.708.707A7.48 7.48 0 0 1 13.025 8c0 2.071-.84 3.946-2.197 5.303l.708.707z"/><path d="M10.121 12.596A6.48 6.48 0 0 0 12.025 8a6.48 6.48 0 0 0-1.904-4.596l-.707.707A5.48 5.48 0 0 1 11.025 8a5.48 5.48 0 0 1-1.61 3.89l.706.706z"/><path d="M8.707 11.182A4.5 4.5 0 0 0 10.025 8a4.5 4.5 0 0 0-1.318-3.182L8 5.525A3.5 3.5 0 0 1 9.025 8 3.5 3.5 0 0 1 8 10.475l.707.707zM6.717 3.55A.5.5 0 0 1 7 4v8a.5.5 0 0 1-.812.39L3.825 10.5H1.5A.5.5 0 0 1 1 10V6a.5.5 0 0 1 .5-.5h2.325l2.363-1.89a.5.5 0 0 1 .529-.06z"/>`;
        }

        if (isMuted) {
            stopAudio();
        }
    }

    function formatMarkdown(text) {
        // Replace **bold**
        let formatted = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        
        // Replace * or - bullet points with an arrow
        formatted = formatted.split("\n").map(line => {
            if (line.trim().match(/^[-*]\s/)) {
                return line.replace(/^(\s*)[-*]\s/, "$1➤ ");
            }
            return line;
        }).join("<br>");
        
        // Remove rogue remaining # tags used for markdown headers
        formatted = formatted.replace(/###\s/g, "");
        
        return formatted;
    }

    function appendMessage(text, className) {
        const message = document.createElement("div");
        message.className = `message ${className}`;
        
        const formattedText = (className === "bot-message") ? formatMarkdown(text) : text.replace(/\n/g, "<br>");
        
        message.innerHTML = `
            <div class="message-content">${formattedText}</div>
            <div class="message-time">Just now</div>
        `;
        chatMessages.appendChild(message);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendTypingIndicator() {
        const message = document.createElement("div");
        message.className = "message bot-message";
        message.innerHTML = `
            <div class="message-content"><div class="typing-dots"><span></span><span></span><span></span></div></div>
            <div class="message-time">Just now</div>
        `;
        chatMessages.appendChild(message);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return message;
    }

    function speakText(text, lang) {
        if (isMuted || !("speechSynthesis" in window)) {
            return;
        }

        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text.replace(/[*_#]/g, "").replace(/<[^>]+>/g, ""));
        const simpleLang = lang ? lang.split("-")[0] : "en";
        const voiceMap = {
            en: "en-US",
            hi: "hi-IN",
            gu: "gu-IN",
            es: "es-ES",
            fr: "fr-FR",
            de: "de-DE",
            ja: "ja-JP",
            zh: "zh-CN",
            ar: "ar-SA",
            ru: "ru-RU",
            pt: "pt-PT"
        };

        utterance.lang = voiceMap[simpleLang] || "en-US";
        utterance.rate = 1.05;
        window.speechSynthesis.speak(utterance);
    }

    function clearConversation() {
        chatMessages.innerHTML = "";
        appendMessage("Hello! I am Vihil InfoTech's AI assistant. Ask about services, technologies, team, or contact details.", "bot-message");
    }

    function updateClock() {
        if (!topbarTime) return;
        const now = new Date();
        topbarTime.textContent = new Intl.DateTimeFormat([], {
            hour: "numeric",
            minute: "2-digit"
        }).format(now);
    }

    updateClock();
    setInterval(updateClock, 1000);

    if (muteBtn) {
        muteBtn.addEventListener("click", () => setMuted(!isMuted));
    }

    if (clearBtn) {
        clearBtn.addEventListener("click", clearConversation);
    }

    modeButtons.forEach((button) => {
        button.addEventListener("click", () => {
            modeButtons.forEach((item) => item.classList.remove("active"));
            button.classList.add("active");
            currentMode = button.dataset.mode || "type";
            if (currentMode === "speak" && micBtn) {
                micBtn.click();
            }
        });
    });

    async function submitQuery(text, wasSpoken = false) {
        stopAudio(); // Stop any currently playing audio so voices don't overlap
        
        appendMessage(text, "user-message");
        const typing = appendTypingIndicator();

        try {
            const response = await fetch("/api/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    query: text, 
                    lang: langSelect ? langSelect.value : "auto",
                    voice_response: !isMuted
                })
            });

            typing.remove();

            if (!response.ok) {
                appendMessage("Error generating answer. Please try again.", "bot-message");
                return;
            }

            const data = await response.json();
            appendMessage(data.answer, "bot-message");

            if (!isMuted) {
                if (data.audio) {
                    currentPlayingAudio = new Audio(`data:audio/mp3;base64,${data.audio}`);
                    currentPlayingAudio.play().catch(() => speakText(data.answer, data.lang));
                } else {
                    speakText(data.answer, data.lang);
                }
            }
        } catch (error) {
            typing.remove();
            appendMessage("Failed to communicate with the server. Please check that FastAPI is running.", "bot-message");
            console.error(error);
        }
    }

    chatForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const text = userInput.value.trim();
        if (!text) {
            return;
        }
        userInput.value = "";
        submitQuery(text, false);
    });



    if (micBtn && ("SpeechRecognition" in window || "webkitSpeechRecognition" in window)) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        
        let finalTranscript = "";
        recognition.maxAlternatives = 1;

        const basePlaceholder = userInput.placeholder;

        if (navigator.permissions && navigator.permissions.query) {
            navigator.permissions.query({ name: "microphone" }).then((status) => {
                micPermissionDenied = status.state === "denied";
                if (micPermissionDenied) {
                    micBtn.title = "Microphone permission is denied in this browser";
                    micBtn.classList.add("blocked");
                }
                status.onchange = () => {
                    micPermissionDenied = status.state === "denied";
                    micBtn.classList.toggle("blocked", micPermissionDenied);
                };
            }).catch(() => {});
        }

        recognition.onresult = (event) => {
            let interimTranscript = "";
            finalTranscript = "";
            
            for (let i = 0; i < event.results.length; i++) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript + " ";
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }
            
            userInput.value = finalTranscript + interimTranscript;
        };

        recognition.onerror = (event) => {
            isListening = false;
            micBtn.classList.remove("recording");
            userInput.placeholder = micPermissionDenied ? "Allow microphone permission to use Speak" : basePlaceholder;
            if (event.error === "not-allowed" || event.error === "service-not-allowed") {
                micBtn.classList.add("blocked");
            }
        };

        recognition.onstart = () => {
            isListening = true;
            micBtn.classList.add("recording");
            userInput.placeholder = "Listening... speak now";
        };

        recognition.onend = () => {
            isListening = false;
            micBtn.classList.remove("recording");
            userInput.placeholder = basePlaceholder;
            
            const text = userInput.value.trim();
            if (text) {
                userInput.value = "";
                submitQuery(text, true);
            }
        };

        micBtn.addEventListener("click", () => {
            if (!recognition) {
                return;
            }

            if (micPermissionDenied) {
                userInput.placeholder = "Allow microphone permission to use Speak";
                return;
            }

            if (isListening) {
                recognition.stop();
                return;
            }

            finalTranscript = "";
            userInput.value = "";

            if (isMuted && "speechSynthesis" in window) {
                window.speechSynthesis.cancel();
            }

            const selectedLang = langSelect ? langSelect.value : "auto";
            const langMap = {
                en: "en-US",
                hi: "hi-IN",
                gu: "gu-IN",
                es: "es-ES",
                fr: "fr-FR",
                de: "de-DE",
                ja: "ja-JP",
                zh: "zh-CN",
                ar: "ar-SA",
                ru: "ru-RU",
                pt: "pt-PT"
            };
            recognition.lang = selectedLang !== "auto" ? (langMap[selectedLang] || selectedLang) : "en-US";

            try {
                recognition.start();
            } catch (error) {
                isListening = false;
                micBtn.classList.remove("recording");
                userInput.placeholder = basePlaceholder;
                appendMessage("Speak could not start. Check microphone permission and try again.", "bot-message");
                console.error(error);
            }
        });
    } else if (micBtn) {
        micBtn.addEventListener("click", () => alert("Speech recognition is not supported in this browser. Please use Chrome or Edge."));
    }

    clearConversation();
});
