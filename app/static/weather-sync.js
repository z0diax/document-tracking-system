(function() {
    'use strict';

    const hoverListeners = [];

    function initWeatherSync() {
        const body = document.body;
        if (!body) return;

        // Check if Weather Auto mode is active
        const themeMode = body.dataset.themeMode || '';
        if (themeMode !== 'weather_auto') {
            // If not weather_auto, remove any existing weather effects
            const existing = document.getElementById('weather-navbar-effects');
            if (existing) existing.remove();
            
            // Remove mascot if it exists
            const mascot = document.querySelector('.navbar-brand .weather-mascot');
            if (mascot) mascot.remove();

            // Remove test switcher if it exists
            const testPanel = document.getElementById('weather-test-panel');
            if (testPanel) testPanel.remove();
            return;
        }

        const effectiveTheme = (body.dataset.seasonTheme || '').toLowerCase();
        const nav = document.querySelector('nav.navbar');
        if (!nav) return;

        // Ensure the effects container exists
        let effectsContainer = document.getElementById('weather-navbar-effects');
        if (!effectsContainer) {
            effectsContainer = document.createElement('div');
            effectsContainer.id = 'weather-navbar-effects';
            effectsContainer.style.position = 'absolute';
            effectsContainer.style.inset = '0';
            effectsContainer.style.pointerEvents = 'none';
            effectsContainer.style.zIndex = '1';
            effectsContainer.style.overflow = 'hidden';
            nav.insertBefore(effectsContainer, nav.firstChild);
        } else {
            // Clean up old interval/animation callbacks
            if (effectsContainer.cleanup) {
                effectsContainer.cleanup();
            }
            // Clear existing elements
            effectsContainer.innerHTML = '';
        }

        // Setup interactive mascot next to brand logo
        const brand = nav.querySelector('.navbar-brand');
        if (brand) {
            let mascot = brand.querySelector('.weather-mascot');
            if (!mascot) {
                mascot = document.createElement('span');
                mascot.className = 'weather-mascot ms-2';
                mascot.style.fontSize = '1.6rem';
                mascot.style.display = 'inline-block';
                mascot.style.transition = 'transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                mascot.style.cursor = 'pointer';
                mascot.style.transformOrigin = 'center';
                
                // Super premium wiggle, pop, and rotate effect on hover!
                mascot.addEventListener('mouseenter', () => {
                    mascot.style.transform = 'scale(1.35) rotate(15deg) translateY(-3px)';
                    mascot.style.filter = 'drop-shadow(0 4px 8px rgba(0,0,0,0.15))';
                });
                mascot.addEventListener('mouseleave', () => {
                    mascot.style.transform = 'scale(1) rotate(0deg) translateY(0)';
                    mascot.style.filter = 'none';
                });
                
                // Add click effect: mascot does a full spin!
                mascot.addEventListener('click', () => {
                    mascot.style.transition = 'transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)';
                    mascot.style.transform = 'scale(1.4) rotate(360deg)';
                    setTimeout(() => {
                        mascot.style.transition = 'transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                        mascot.style.transform = 'scale(1) rotate(0deg)';
                    }, 600);
                });
                
                brand.appendChild(mascot);
            }
            
            const mascots = {
                sunny: '☀️',
                cloudy: '🌤️',
                windy: '🍃',
                rainy: '🐸',
                thunderstorm: '⛈️',
                winter: '☃️'
            };
            mascot.textContent = mascots[effectiveTheme] || '';
        }

        // Setup floating test weather switcher button
        // setupTestSwitcher(body, nav, effectiveTheme);

        // Initialize theme-specific effect
        if (effectiveTheme === 'sunny') {
            renderSunnyEffect(effectsContainer, nav);
        } else if (effectiveTheme === 'cloudy') {
            renderCloudyEffect(effectsContainer, nav);
        } else if (effectiveTheme === 'windy') {
            renderWindyEffect(effectsContainer, nav);
        } else if (effectiveTheme === 'rainy') {
            renderRainyEffect(effectsContainer, nav, false); // gentle rain, dark clouds
        } else if (effectiveTheme === 'thunderstorm') {
            renderRainyEffect(effectsContainer, nav, true); // heavy rain, storm clouds, lightning
        } else if (effectiveTheme === 'winter') {
            renderWinterEffect(effectsContainer, nav); // snowy canvas
        }
    }

    // --- Shared helpers for hover particles ---
    function setupHoverListeners(nav, hoverParticles, theme) {
        removeHoverListeners();

        const interactiveElements = nav.querySelectorAll('a, button, .nav-link, .dropdown-item, .navbar-brand');
        
        const mouseEnterHandler = (e) => {
            const el = e.currentTarget;
            if (el.classList.contains('weather-mascot')) return; // skip mascot container itself
            const rect = el.getBoundingClientRect();
            const navRect = nav.getBoundingClientRect();
            const x = rect.left - navRect.left + rect.width / 2;
            const y = rect.top - navRect.top + rect.height / 2;
            spawnHoverParticles(x, y, theme, hoverParticles);
        };

        interactiveElements.forEach(el => {
            el.addEventListener('mouseenter', mouseEnterHandler);
            hoverListeners.push({ el, handler: mouseEnterHandler });
        });
    }

    function removeHoverListeners() {
        while (hoverListeners.length > 0) {
            const { el, handler } = hoverListeners.pop();
            if (el) el.removeEventListener('mouseenter', handler);
        }
    }

    function spawnHoverParticles(x, y, theme, hoverParticles) {
        if (theme === 'sunny') {
            for (let i = 0; i < 8; i++) {
                const angle = Math.random() * Math.PI * 2;
                const speed = 1 + Math.random() * 2;
                hoverParticles.push({
                    x, y,
                    vx: Math.cos(angle) * speed,
                    vy: Math.sin(angle) * speed,
                    size: 2.5 + Math.random() * 3,
                    color: `rgba(253, 224, 71, ${0.7 + Math.random() * 0.3})`,
                    life: 1.0,
                    decay: 0.03 + Math.random() * 0.02,
                    type: 'sparkle'
                });
            }
        } else if (theme === 'cloudy') {
            for (let i = 0; i < 5; i++) {
                hoverParticles.push({
                    x: x + (Math.random() - 0.5) * 15,
                    y: y + (Math.random() - 0.5) * 10,
                    vx: (Math.random() - 0.5) * 0.6,
                    vy: (Math.random() - 0.5) * 0.4,
                    size: 4 + Math.random() * 6,
                    color: 'rgba(255, 255, 255, 0.28)',
                    life: 1.0,
                    decay: 0.02 + Math.random() * 0.02,
                    type: 'cloud'
                });
            }
        } else if (theme === 'windy') {
            for (let i = 0; i < 4; i++) {
                hoverParticles.push({
                    x, y,
                    vx: 1.5 + Math.random() * 2,
                    vy: -0.5 + Math.random() * 1,
                    size: 3 + Math.random() * 3,
                    angle: Math.random() * Math.PI,
                    rotSpeed: -0.05 + Math.random() * 0.1,
                    color: ['rgba(52, 211, 153, 0.65)', 'rgba(253, 224, 71, 0.55)', 'rgba(125, 211, 252, 0.5)'][Math.floor(Math.random() * 3)],
                    life: 1.0,
                    decay: 0.015,
                    type: 'leaf'
                });
            }
        } else if (theme === 'rainy' || theme === 'thunderstorm') {
            for (let i = 0; i < 6; i++) {
                hoverParticles.push({
                    x, y: y + 8,
                    vx: -1.5 + Math.random() * 3,
                    vy: -1.5 - Math.random() * 1.5,
                    gravity: 0.12,
                    size: 1.5 + Math.random() * 1.5,
                    color: 'rgba(186, 230, 253, 0.75)',
                    life: 1.0,
                    decay: 0.025,
                    type: 'splash'
                });
            }
        } else if (theme === 'winter') {
            for (let i = 0; i < 5; i++) {
                hoverParticles.push({
                    x: x + (Math.random() - 0.5) * 20,
                    y,
                    vx: -0.5 + Math.random() * 1,
                    vy: 0.5 + Math.random() * 0.8,
                    size: 1.5 + Math.random() * 2,
                    wobble: Math.random() * Math.PI,
                    wobbleSpeed: 0.05,
                    color: 'rgba(255, 255, 255, 0.8)',
                    life: 1.0,
                    decay: 0.015 + Math.random() * 0.01,
                    type: 'snow'
                });
            }
        }
    }

    function updateHoverParticles(ctx, hoverParticles) {
        for (let i = hoverParticles.length - 1; i >= 0; i--) {
            const p = hoverParticles[i];
            p.life -= p.decay;
            if (p.life <= 0) {
                hoverParticles.splice(i, 1);
                continue;
            }

            if (p.gravity) {
                p.vy += p.gravity;
            }
            p.x += p.vx;
            p.y += p.vy;

            ctx.save();
            ctx.globalAlpha = p.life;

            if (p.type === 'sparkle') {
                ctx.fillStyle = p.color;
                ctx.beginPath();
                ctx.moveTo(p.x, p.y - p.size);
                ctx.lineTo(p.x + p.size * 0.3, p.y - p.size * 0.3);
                ctx.lineTo(p.x + p.size, p.y);
                ctx.lineTo(p.x + p.size * 0.3, p.y + p.size * 0.3);
                ctx.lineTo(p.x, p.y + p.size);
                ctx.lineTo(p.x - p.size * 0.3, p.y + p.size * 0.3);
                ctx.lineTo(p.x - p.size, p.y);
                ctx.lineTo(p.x - p.size * 0.3, p.y - p.size * 0.3);
                ctx.closePath();
                ctx.fill();
            } else if (p.type === 'cloud') {
                ctx.fillStyle = p.color;
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fill();
            } else if (p.type === 'leaf') {
                p.angle += p.rotSpeed;
                ctx.translate(p.x, p.y);
                ctx.rotate(p.angle);
                ctx.fillStyle = p.color;
                ctx.beginPath();
                ctx.moveTo(0, -p.size);
                ctx.quadraticCurveTo(p.size * 1.5, 0, 0, p.size);
                ctx.quadraticCurveTo(-p.size * 1.5, 0, 0, -p.size);
                ctx.fill();
            } else if (p.type === 'splash') {
                ctx.strokeStyle = p.color;
                ctx.lineWidth = p.size;
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(p.x - p.vx * 1.2, p.y - p.vy * 1.2);
                ctx.stroke();
            } else if (p.type === 'snow') {
                p.wobble += p.wobbleSpeed;
                ctx.fillStyle = p.color;
                ctx.beginPath();
                ctx.arc(p.x + Math.sin(p.wobble) * 3, p.y, p.size, 0, Math.PI * 2);
                ctx.fill();
            }

            ctx.restore();
        }
    }

    function setupCanvas(container, nav) {
        const canvas = document.createElement('canvas');
        canvas.style.position = 'absolute';
        canvas.style.inset = '0';
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.pointerEvents = 'none';
        container.appendChild(canvas);

        const ctx = canvas.getContext('2d');
        function resize() {
            canvas.width = nav.offsetWidth;
            canvas.height = nav.offsetHeight;
        }
        resize();
        window.addEventListener('resize', resize);
        return { canvas, ctx, resize };
    }

    // --- Test Weather Switcher Widget ---
    function setupTestSwitcher(body, nav, currentTheme) {
        let testPanel = document.getElementById('weather-test-panel');
        if (!testPanel) {
            testPanel = document.createElement('div');
            testPanel.id = 'weather-test-panel';
            testPanel.style.position = 'fixed';
            testPanel.style.bottom = '20px';
            testPanel.style.right = '20px';
            testPanel.style.zIndex = '2000';
            testPanel.style.display = 'flex';
            testPanel.style.flexDirection = 'column';
            testPanel.style.alignItems = 'flex-end';
            testPanel.style.fontFamily = 'system-ui, -apple-system, sans-serif';
            
            const mainBtn = document.createElement('button');
            mainBtn.id = 'weather-test-toggle';
            mainBtn.className = 'btn btn-sm btn-dark rounded-pill px-3 shadow';
            mainBtn.style.background = 'rgba(15, 23, 42, 0.85)';
            mainBtn.style.color = '#fff';
            mainBtn.style.border = '1px solid rgba(255, 255, 255, 0.2)';
            mainBtn.style.backdropFilter = 'blur(8px)';
            mainBtn.style.webkitBackdropFilter = 'blur(8px)';
            mainBtn.style.display = 'flex';
            mainBtn.style.alignItems = 'center';
            mainBtn.style.gap = '6px';
            mainBtn.style.fontSize = '0.8rem';
            mainBtn.style.fontWeight = '500';
            mainBtn.innerHTML = `<span>🌦️ Test Weather</span> <i class="fas fa-chevron-up" id="weather-test-icon" style="transition: transform 0.3s ease;"></i>`;
            
            const optionsDiv = document.createElement('div');
            optionsDiv.id = 'weather-test-options';
            optionsDiv.style.position = 'absolute';
            optionsDiv.style.bottom = '36px';
            optionsDiv.style.right = '0';
            optionsDiv.style.background = 'rgba(15, 23, 42, 0.9)';
            optionsDiv.style.border = '1px solid rgba(255, 255, 255, 0.15)';
            optionsDiv.style.borderRadius = '10px';
            optionsDiv.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.25)';
            optionsDiv.style.padding = '6px';
            optionsDiv.style.display = 'none';
            optionsDiv.style.flexDirection = 'column';
            optionsDiv.style.gap = '3px';
            optionsDiv.style.minWidth = '130px';
            optionsDiv.style.backdropFilter = 'blur(10px)';
            optionsDiv.style.webkitBackdropFilter = 'blur(10px)';
            
            const weatherOptions = [
                { id: 'sunny', label: '☀️ Sunny' },
                { id: 'cloudy', label: '🌤️ Cloudy' },
                { id: 'windy', label: '🍃 Windy' },
                { id: 'rainy', label: '🐸 Rainy' },
                { id: 'thunderstorm', label: '⛈️ Thunderstorm' },
                { id: 'winter', label: '☃️ Winter' }
            ];
            
            weatherOptions.forEach(opt => {
                const btn = document.createElement('button');
                btn.className = 'btn btn-sm btn-link text-start text-white text-decoration-none px-2 py-1 w-100';
                btn.style.fontSize = '0.75rem';
                btn.style.borderRadius = '6px';
                btn.style.transition = 'background 0.2s ease';
                btn.textContent = opt.label;
                btn.addEventListener('mouseenter', () => {
                    btn.style.background = 'rgba(255, 255, 255, 0.1)';
                });
                btn.addEventListener('mouseleave', () => {
                    btn.style.background = 'transparent';
                });
                btn.addEventListener('click', () => {
                    body.dataset.seasonTheme = opt.id;
                    optionsDiv.style.display = 'none';
                    document.getElementById('weather-test-icon').style.transform = 'rotate(0deg)';
                    initWeatherSync();
                });
                optionsDiv.appendChild(btn);
            });
            
            mainBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const icon = document.getElementById('weather-test-icon');
                if (optionsDiv.style.display === 'none') {
                    optionsDiv.style.display = 'flex';
                    icon.style.transform = 'rotate(180deg)';
                } else {
                    optionsDiv.style.display = 'none';
                    icon.style.transform = 'rotate(0deg)';
                }
            });
            
            document.addEventListener('click', () => {
                optionsDiv.style.display = 'none';
                const icon = document.getElementById('weather-test-icon');
                if (icon) icon.style.transform = 'rotate(0deg)';
            });
            
            testPanel.appendChild(optionsDiv);
            testPanel.appendChild(mainBtn);
            document.body.appendChild(testPanel);
        }
    }

    // --- Sunny Theme: Glowing rotating sunburst + light sparkles ---
    function renderSunnyEffect(container, nav) {
        const sunDiv = document.createElement('div');
        sunDiv.innerHTML = `
            <svg viewBox="0 0 100 100" class="weather-sun-icon" style="position: absolute; top: -20px; left: -10px; width: 100px; height: 100px; filter: drop-shadow(0 0 15px rgba(253, 224, 71, 0.6)); pointer-events: none; z-index: 2;">
                <circle cx="50" cy="50" r="22" fill="#fffdf5" />
                <g class="weather-sun-rays" style="transform-origin: 50px 50px; animation: weather-sun-spin 25s linear infinite;">
                    <line x1="50" y1="10" x2="50" y2="20" stroke="#fde047" stroke-width="4.5" stroke-linecap="round" />
                    <line x1="50" y1="80" x2="50" y2="90" stroke="#fde047" stroke-width="4.5" stroke-linecap="round" />
                    <line x1="10" y1="50" x2="20" y2="50" stroke="#fde047" stroke-width="4.5" stroke-linecap="round" />
                    <line x1="80" y1="50" x2="90" y2="50" stroke="#fde047" stroke-width="4.5" stroke-linecap="round" />
                    <line x1="22" y1="22" x2="29" y2="29" stroke="#fde047" stroke-width="4.5" stroke-linecap="round" />
                    <line x1="71" y1="71" x2="78" y2="78" stroke="#fde047" stroke-width="4.5" stroke-linecap="round" />
                    <line x1="78" y1="22" x2="71" y2="29" stroke="#fde047" stroke-width="4.5" stroke-linecap="round" />
                    <line x1="29" y1="71" x2="22" y2="78" stroke="#fde047" stroke-width="4.5" stroke-linecap="round" />
                </g>
            </svg>
            <style>
                @keyframes weather-sun-spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            </style>
        `;
        container.appendChild(sunDiv);

        const { canvas, ctx } = setupCanvas(container, nav);
        const sparkles = [];
        const maxSparkles = 12;

        for (let i = 0; i < maxSparkles; i++) {
            sparkles.push({
                x: Math.random() * canvas.width,
                y: canvas.height + 10,
                vy: -0.3 - Math.random() * 0.4,
                size: 1 + Math.random() * 2,
                opacity: 0.15 + Math.random() * 0.25,
                phase: Math.random() * Math.PI
            });
        }

        let active = true;
        const hoverParticles = [];

        function animate() {
            if (!active || !canvas.isConnected) return;
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            sparkles.forEach(s => {
                s.phase += 0.02;
                ctx.beginPath();
                ctx.arc(s.x + Math.sin(s.phase) * 6, s.y, s.size, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(253, 224, 71, ${s.opacity * (0.6 + Math.sin(s.phase) * 0.4)})`;
                ctx.fill();

                s.y += s.vy;
                if (s.y < -10) {
                    s.y = canvas.height + 10;
                    s.x = Math.random() * canvas.width;
                }
            });

            updateHoverParticles(ctx, hoverParticles);
            requestAnimationFrame(animate);
        }

        animate();
        setupHoverListeners(nav, hoverParticles, 'sunny');
        container.cleanup = () => {
            active = false;
            removeHoverListeners();
        };
    }

    // --- Cloudy Theme: Translucent clouds drifting with parallax + background mist ---
    function renderCloudyEffect(container, nav) {
        const cloudSVG = `
            <svg viewBox="0 0 64 40" class="weather-cloud-item" style="position: absolute; fill: rgba(255,255,255,0.22); filter: drop-shadow(0 4px 6px rgba(0,0,0,0.05)); pointer-events: none; z-index: 2;">
                <path d="M18 30h28a10 10 0 0 0 0-20 9.5 9.5 0 0 0-6.5 2.5 13 13 0 0 0-23.5 7.5 10 10 0 0 0 2 10z" />
            </svg>
        `;

        const configs = [
            { top: '4px', width: '68px', duration: '35s', delay: '-5s', opacity: 0.2 },
            { top: '15px', width: '54px', duration: '48s', delay: '-18s', opacity: 0.15 },
            { top: '2px', width: '76px', duration: '42s', delay: '-30s', opacity: 0.25 }
        ];

        configs.forEach((cfg) => {
            const div = document.createElement('div');
            div.innerHTML = cloudSVG.trim();
            const svg = div.firstChild;
            svg.style.top = cfg.top;
            svg.style.width = cfg.width;
            svg.style.height = 'auto';
            svg.style.opacity = cfg.opacity;
            svg.style.animation = `weather-cloud-drift ${cfg.duration} linear ${cfg.delay} infinite`;
            container.appendChild(svg);
        });

        if (!document.getElementById('weather-drift-style')) {
            const style = document.createElement('style');
            style.id = 'weather-drift-style';
            style.innerHTML = `
                @keyframes weather-cloud-drift {
                    0% { transform: translateX(-120px); }
                    100% { transform: translateX(calc(100vw + 120px)); }
                }
            `;
            document.head.appendChild(style);
        }

        const { canvas, ctx } = setupCanvas(container, nav);
        let active = true;
        const hoverParticles = [];

        function animate() {
            if (!active || !canvas.isConnected) return;
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            const pulse = 0.05 + Math.sin(Date.now() * 0.001) * 0.02;
            const grad = ctx.createLinearGradient(0, 0, 0, canvas.height);
            grad.addColorStop(0, `rgba(255, 255, 255, ${pulse})`);
            grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
            ctx.fillStyle = grad;
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            updateHoverParticles(ctx, hoverParticles);
            requestAnimationFrame(animate);
        }

        animate();
        setupHoverListeners(nav, hoverParticles, 'cloudy');
        container.cleanup = () => {
            active = false;
            removeHoverListeners();
        };
    }

    // --- Windy Theme: Wind lines and drifting leaves ---
    function renderWindyEffect(container, nav) {
        const { canvas, ctx } = setupCanvas(container, nav);
        
        const lines = [];
        const maxLines = 8;
        const leaves = [];
        const maxLeaves = 6;

        for (let i = 0; i < maxLines; i++) {
            lines.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                length: 50 + Math.random() * 80,
                speed: 4 + Math.random() * 4,
                opacity: 0.08 + Math.random() * 0.12
            });
        }

        for (let i = 0; i < maxLeaves; i++) {
            leaves.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                size: 4 + Math.random() * 5,
                speedX: 2 + Math.random() * 3,
                speedY: -0.5 + Math.random() * 1,
                wobbleSpeed: 0.02 + Math.random() * 0.03,
                wobbleRange: 5 + Math.random() * 10,
                angle: Math.random() * Math.PI,
                rotSpeed: 0.01 + Math.random() * 0.02,
                color: ['rgba(46, 204, 113, 0.4)', 'rgba(39, 174, 96, 0.35)', 'rgba(241, 196, 15, 0.3)'][Math.floor(Math.random() * 3)]
            });
        }

        function drawLeaf(ctx, x, y, size, angle, color) {
            ctx.save();
            ctx.translate(x, y);
            ctx.rotate(angle);
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.moveTo(0, -size);
            ctx.quadraticCurveTo(size * 1.5, 0, 0, size);
            ctx.quadraticCurveTo(-size * 1.5, 0, 0, -size);
            ctx.fill();
            ctx.restore();
        }

        let active = true;
        const hoverParticles = [];

        function animate() {
            if (!active || !canvas.isConnected) return;
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            ctx.lineWidth = 1.2;
            lines.forEach(l => {
                ctx.strokeStyle = `rgba(255, 255, 255, ${l.opacity})`;
                ctx.beginPath();
                ctx.moveTo(l.x, l.y);
                ctx.lineTo(l.x + l.length, l.y);
                ctx.stroke();

                l.x += l.speed;
                if (l.x > canvas.width) {
                    l.x = -l.length;
                    l.y = Math.random() * canvas.height;
                    l.speed = 4 + Math.random() * 4;
                }
            });

            leaves.forEach(lf => {
                lf.angle += lf.rotSpeed;
                const currentY = lf.y + Math.sin(Date.now() * lf.wobbleSpeed) * (lf.wobbleRange / 10);
                drawLeaf(ctx, lf.x, currentY, lf.size, lf.angle, lf.color);

                lf.x += lf.speedX;
                lf.y += lf.speedY;

                if (lf.x > canvas.width + 20) {
                    lf.x = -20;
                    lf.y = Math.random() * canvas.height;
                }
            });

            updateHoverParticles(ctx, hoverParticles);
            requestAnimationFrame(animate);
        }

        animate();
        setupHoverListeners(nav, hoverParticles, 'windy');
        container.cleanup = () => {
            active = false;
            removeHoverListeners();
        };
    }

    // --- Rainy & Thunderstorm Themes ---
    function renderRainyEffect(container, nav, isThunderstorm) {
        const cloudSVG = `
            <svg viewBox="0 0 64 40" class="storm-cloud-svg" style="position: absolute; fill: rgba(30, 41, 59, 0.45); filter: drop-shadow(0 4px 8px rgba(0,0,0,0.15)); pointer-events: none; z-index: 2; transition: fill 0.1s ease, filter 0.1s ease;">
                <path d="M18 30h28a10 10 0 0 0 0-20 9.5 9.5 0 0 0-6.5 2.5 13 13 0 0 0-23.5 7.5 10 10 0 0 0 2 10z" />
            </svg>
        `;
        const cloudConfigs = [
            { top: '-4px', left: '10%', width: '85px', opacity: 0.4 },
            { top: '-2px', left: '45%', width: '70px', opacity: 0.35 },
            { top: '-6px', left: '75%', width: '90px', opacity: 0.45 }
        ];

        const cloudElements = [];
        cloudConfigs.forEach(cfg => {
            const div = document.createElement('div');
            div.innerHTML = cloudSVG.trim();
            const svg = div.firstChild;
            svg.style.top = cfg.top;
            svg.style.left = cfg.left;
            svg.style.width = cfg.width;
            svg.style.height = 'auto';
            svg.style.opacity = cfg.opacity;
            container.appendChild(svg);
            cloudElements.push(svg);
        });

        const { canvas, ctx } = setupCanvas(container, nav);
        const particles = [];
        const maxParticles = isThunderstorm ? 50 : 25;

        for (let i = 0; i < maxParticles; i++) {
            particles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                vy: (isThunderstorm ? 5 : 3.5) + Math.random() * 2.5,
                vx: isThunderstorm ? -1.5 - Math.random() * 1 : -0.5 - Math.random() * 0.5,
                length: 6 + Math.random() * 8,
                opacity: 0.15 + Math.random() * 0.25
            });
        }

        let flashOpacity = 0;
        let nextFlashTime = Date.now() + 4000 + Math.random() * 6000;
        let flashTimeout = null;

        function triggerLightning() {
            let step = 0;
            const sequence = [0.6, 0.1, 0.8, 0.2, 0.9, 0.0];
            function flash() {
                if (step >= sequence.length) {
                    flashOpacity = 0;
                    nextFlashTime = Date.now() + 5000 + Math.random() * 8000;
                    return;
                }
                flashOpacity = sequence[step];
                step++;
                flashTimeout = setTimeout(flash, 50 + Math.random() * 60);
            }
            flash();
        }

        let active = true;
        const hoverParticles = [];

        function animate() {
            if (!active || !canvas.isConnected) return;
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            if (isThunderstorm && Date.now() > nextFlashTime) {
                triggerLightning();
            }

            if (flashOpacity > 0) {
                ctx.fillStyle = `rgba(255, 255, 255, ${flashOpacity * 0.4})`;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                nav.style.transform = `translate(${(Math.random() - 0.5) * 3}px, ${(Math.random() - 0.5) * 3}px)`;
                
                cloudElements.forEach(el => {
                    el.style.fill = 'rgba(148, 163, 184, 0.85)';
                    el.style.filter = 'drop-shadow(0 0 12px rgba(255, 255, 255, 0.6))';
                });
            } else {
                nav.style.transform = 'none';
                cloudElements.forEach(el => {
                    el.style.fill = 'rgba(30, 41, 59, 0.45)';
                    el.style.filter = 'drop-shadow(0 4px 8px rgba(0,0,0,0.15))';
                });
            }

            ctx.lineWidth = 1;
            particles.forEach(p => {
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(p.x + p.vx * 1.5, p.y + p.length);
                ctx.strokeStyle = `rgba(186, 230, 253, ${p.opacity})`;
                ctx.stroke();

                p.y += p.vy;
                p.x += p.vx;

                if (p.y > canvas.height) {
                    ctx.strokeStyle = `rgba(186, 230, 253, ${p.opacity * 0.5})`;
                    ctx.lineWidth = 0.8;
                    ctx.beginPath();
                    ctx.ellipse(p.x, canvas.height - 2, 4 + Math.random() * 4, 1.2, 0, 0, Math.PI * 2);
                    ctx.stroke();

                    p.y = -10;
                    p.x = Math.random() * canvas.width;
                }
            });

            updateHoverParticles(ctx, hoverParticles);
            requestAnimationFrame(animate);
        }

        animate();
        setupHoverListeners(nav, hoverParticles, isThunderstorm ? 'thunderstorm' : 'rainy');
        container.cleanup = () => {
            active = false;
            nav.style.transform = 'none';
            if (flashTimeout) clearTimeout(flashTimeout);
            removeHoverListeners();
        };
    }

    // --- Winter Theme: Soft falling snowflakes ---
    function renderWinterEffect(container, nav) {
        const { canvas, ctx } = setupCanvas(container, nav);
        const flakes = [];
        const maxFlakes = 30;

        for (let i = 0; i < maxFlakes; i++) {
            flakes.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                radius: 1 + Math.random() * 2,
                vy: 0.6 + Math.random() * 0.8,
                vx: -0.3 + Math.random() * 0.6,
                wobble: Math.random() * Math.PI,
                wobbleSpeed: 0.01 + Math.random() * 0.02,
                opacity: 0.3 + Math.random() * 0.5
            });
        }

        let active = true;
        const hoverParticles = [];

        function animate() {
            if (!active || !canvas.isConnected) return;
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            flakes.forEach(f => {
                ctx.beginPath();
                ctx.arc(f.x + Math.sin(f.wobble) * 2, f.y, f.radius, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(255, 255, 255, ${f.opacity})`;
                ctx.fill();

                f.y += f.vy;
                f.x += f.vx;
                f.wobble += f.wobbleSpeed;

                if (f.y > canvas.height) {
                    f.y = -5;
                    f.x = Math.random() * canvas.width;
                    f.wobble = Math.random() * Math.PI;
                }
            });

            updateHoverParticles(ctx, hoverParticles);
            requestAnimationFrame(animate);
        }

        animate();
        setupHoverListeners(nav, hoverParticles, 'winter');
        container.cleanup = () => {
            active = false;
            removeHoverListeners();
        };
    }

    document.addEventListener('DOMContentLoaded', initWeatherSync);

    const originalApplyEffectiveTheme = window.applyEffectiveTheme;
    window.applyEffectiveTheme = function(theme) {
        if (typeof originalApplyEffectiveTheme === 'function') {
            originalApplyEffectiveTheme(theme);
        }
        setTimeout(initWeatherSync, 50);
    };
})();
