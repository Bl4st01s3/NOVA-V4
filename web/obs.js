document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("nova-canvas");
    const ctx = canvas.getContext("2d");

    let width, height, centerX, centerY;

    // Core state
    let currentState = 'idle'; // idle, talking, error

    // Colors mapped to states
    const colors = {
        idle: { r: 0, g: 243, b: 255 }, // Cyan
        talking: { r: 188, g: 19, b: 254 }, // Purple
        error: { r: 255, g: 50, b: 50 } // Red
    };

    // Current animated color (starts as idle)
    let currentColor = { ...colors.idle };

    // Wave parameters
    const waveColor = { r: 188, g: 19, b: 254 }; // Always purple
    let waveAmplitudeTarget = 20;
    let waveAmplitude = 20;
    let waveFrequency = 0.01;
    let waveSpeed = 0.05;
    let waveOffset = 0;

    // Orb parameters
    let orbRadius = 80;
    let breathAngle = 0;

    // Particles
    const orbParticles = [];
    const orbitingParticles = [];
    const waveParticles = [];

    function initParticles() {
        // Internal orb particles (the node network effect)
        for(let i=0; i<60; i++) {
            orbParticles.push({
                x: (Math.random() - 0.5) * 2,
                y: (Math.random() - 0.5) * 2,
                size: Math.random() * 2 + 0.5,
                speedX: (Math.random() - 0.5) * 0.02,
                speedY: (Math.random() - 0.5) * 0.02
            });
        }

        // Outer orbiting particles
        for(let i=0; i<3; i++) {
            orbitingParticles.push({
                angle: (i / 3) * Math.PI * 2,
                distance: orbRadius + 40 + Math.random() * 20,
                speed: 0.02 + Math.random() * 0.01,
                size: 3 + Math.random() * 2,
                trail: []
            });
        }

        // Wave satellite particles
        for(let i=0; i<30; i++) {
            waveParticles.push({
                x: Math.random() * window.innerWidth, // Random start X
                yOffset: (Math.random() - 0.5) * 60, // Random vertical offset from the wave center
                size: Math.random() * 1.5 + 0.5,
                speedX: 0.5 + Math.random() * 1.5 // Particles flow left to right
            });
        }
    }

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        width = canvas.width;
        height = canvas.height;
        centerX = width / 2;
        centerY = height / 2;
        // Make orb responsive relative to height
        orbRadius = Math.min(width, height) * 0.15;
    }

    window.addEventListener("resize", resize);
    resize();
    initParticles();

    // Lerp helper for smooth transitions
    function lerp(start, end, amt) {
        return (1 - amt) * start + amt * end;
    }

    function updateState() {
        // Smoothly transition colors
        const targetColor = colors[currentState];
        currentColor.r = lerp(currentColor.r, targetColor.r, 0.05);
        currentColor.g = lerp(currentColor.g, targetColor.g, 0.05);
        currentColor.b = lerp(currentColor.b, targetColor.b, 0.05);

        // Update wave amplitude based on state
        if (currentState === 'talking') {
            // Jagged, highly active wave
            waveAmplitudeTarget = 80 + Math.random() * 60;
        } else {
            // Calm, low wave
            waveAmplitudeTarget = 20;
        }
        waveAmplitude = lerp(waveAmplitude, waveAmplitudeTarget, 0.1);

        // Update wave offset
        waveOffset -= waveSpeed;

        // Update breathing
        let breathSpeed = currentState === 'error' ? 0.1 : 0.03;
        breathAngle += breathSpeed;
    }

    function getWaveY(x, isSecondary = false) {
        let y = 0;
        if (!isSecondary) {
            y = Math.sin(x * waveFrequency + waveOffset) * waveAmplitude;
            y += Math.sin(x * waveFrequency * 2.5 + waveOffset * 1.5) * (waveAmplitude * 0.5);
        } else {
            y = Math.cos(x * waveFrequency * 0.8 + waveOffset * 1.2) * (waveAmplitude * 0.8);
        }

        // Taper the wave at the edges
        let distanceToCenter = Math.abs(x - centerX);
        let taper = Math.max(0, 1 - distanceToCenter / (width / 2));
        return y * taper;
    }

    function drawWave() {
        // Main wave
        ctx.beginPath();
        ctx.lineWidth = 3;
        ctx.strokeStyle = `rgba(${waveColor.r}, ${waveColor.g}, ${waveColor.b}, 0.6)`;
        ctx.shadowBlur = 15;
        ctx.shadowColor = `rgba(${waveColor.r}, ${waveColor.g}, ${waveColor.b}, 1)`;

        for (let x = 0; x < width; x += 5) {
            let y = getWaveY(x, false);
            if (x === 0) ctx.moveTo(x, centerY + y);
            else ctx.lineTo(x, centerY + y);
        }
        ctx.stroke();

        // Faint secondary wave
        ctx.beginPath();
        ctx.lineWidth = 1;
        ctx.strokeStyle = `rgba(${waveColor.r}, ${waveColor.g}, ${waveColor.b}, 0.3)`;
        for (let x = 0; x < width; x += 5) {
            let y = getWaveY(x, true);
            if (x === 0) ctx.moveTo(x, centerY + y);
            else ctx.lineTo(x, centerY + y);
        }
        ctx.stroke();
        ctx.shadowBlur = 0; // Reset
    }

    function drawWaveParticles() {
        ctx.strokeStyle = `rgba(${waveColor.r}, ${waveColor.g}, ${waveColor.b}, 0.4)`;
        ctx.fillStyle = `rgba(${waveColor.r}, ${waveColor.g}, ${waveColor.b}, 0.8)`;
        ctx.lineWidth = 0.5;

        // Update and draw nodes
        for (let i = 0; i < waveParticles.length; i++) {
            let p = waveParticles[i];

            // Move horizontally
            p.x += p.speedX;
            // Wrap around screen
            if (p.x > width) {
                p.x = 0;
                p.yOffset = (Math.random() - 0.5) * 60;
            }

            // Calculate actual Y position based on wave + offset
            let waveY = getWaveY(p.x, false);
            let py = centerY + waveY + p.yOffset;

            // Draw particle
            ctx.beginPath();
            ctx.arc(p.x, py, p.size, 0, Math.PI * 2);
            ctx.fill();

            // Draw connecting network lines to nearby particles
            for (let j = i + 1; j < waveParticles.length; j++) {
                let p2 = waveParticles[j];
                let p2WaveY = getWaveY(p2.x, false);
                let p2y = centerY + p2WaveY + p2.yOffset;

                let dist = Math.sqrt(Math.pow(p.x - p2.x, 2) + Math.pow(py - p2y, 2));

                if (dist < 100) {
                    // Fade line based on distance
                    let opacity = 0.4 * (1 - dist / 100);
                    ctx.strokeStyle = `rgba(${waveColor.r}, ${waveColor.g}, ${waveColor.b}, ${opacity})`;
                    ctx.beginPath();
                    ctx.moveTo(p.x, py);
                    ctx.lineTo(p2.x, p2y);
                    ctx.stroke();
                }
            }
        }
    }

    function drawOrb() {
        const currentRadius = orbRadius + Math.sin(breathAngle) * (orbRadius * 0.05);

        const r = Math.round(currentColor.r);
        const g = Math.round(currentColor.g);
        const b = Math.round(currentColor.b);

        // Core glow
        const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, currentRadius * 1.5);
        gradient.addColorStop(0, `rgba(255, 255, 255, 0.9)`);
        gradient.addColorStop(0.2, `rgba(${r}, ${g}, ${b}, 0.8)`);
        gradient.addColorStop(0.6, `rgba(${r}, ${g}, ${b}, 0.2)`);
        gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, currentRadius * 1.5, 0, Math.PI * 2);
        ctx.fill();

        // Internal network particles
        ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.4)`;
        ctx.fillStyle = `rgba(255, 255, 255, 0.8)`;
        ctx.lineWidth = 0.5;

        for(let i=0; i<orbParticles.length; i++) {
            let p = orbParticles[i];
            p.x += p.speedX;
            p.y += p.speedY;

            // Bounce inside sphere
            let dist = Math.sqrt(p.x*p.x + p.y*p.y);
            if (dist > 1) {
                p.speedX *= -1;
                p.speedY *= -1;
            }

            let px = centerX + p.x * currentRadius;
            let py = centerY + p.y * currentRadius;

            ctx.beginPath();
            ctx.arc(px, py, p.size, 0, Math.PI * 2);
            ctx.fill();

            // Draw lines between close particles
            for(let j=i+1; j<orbParticles.length; j++) {
                let p2 = orbParticles[j];
                let p2x = centerX + p2.x * currentRadius;
                let p2y = centerY + p2.y * currentRadius;

                let d = Math.sqrt(Math.pow(px - p2x, 2) + Math.pow(py - p2y, 2));
                if(d < currentRadius * 0.5) {
                    ctx.beginPath();
                    ctx.moveTo(px, py);
                    ctx.lineTo(p2x, p2y);
                    ctx.stroke();
                }
            }
        }
    }

    function drawOrbitingParticles() {
        const r = Math.round(currentColor.r);
        const g = Math.round(currentColor.g);
        const b = Math.round(currentColor.b);

        for (let i = 0; i < orbitingParticles.length; i++) {
            let p = orbitingParticles[i];

            let speedMult = currentState === 'error' ? 3 : (currentState === 'talking' ? 1.5 : 1);
            p.angle += p.speed * speedMult;

            // Calculate 3D orbit effect (squashed circle)
            let x = centerX + Math.cos(p.angle) * p.distance;
            let y = centerY + Math.sin(p.angle) * (p.distance * 0.3); // squash Y for perspective

            // Depth effect (size and opacity based on sine of angle to simulate going behind)
            let depth = Math.sin(p.angle);
            let size = p.size * (1 + depth * 0.3);
            let alpha = 0.5 + depth * 0.5;

            // Save trail
            p.trail.unshift({x, y, size, alpha});
            if (p.trail.length > 20) p.trail.pop();

            // Draw trail
            ctx.shadowBlur = 10;
            ctx.shadowColor = `rgba(${r}, ${g}, ${b}, 1)`;

            ctx.beginPath();
            ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
            ctx.lineWidth = size;
            ctx.lineCap = 'round';
            for (let j = 0; j < p.trail.length; j++) {
                let t = p.trail[j];
                if (j === 0) ctx.moveTo(t.x, t.y);
                else ctx.lineTo(t.x, t.y);
            }
            ctx.stroke();

            // Draw particle core
            ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
            ctx.beginPath();
            ctx.arc(x, y, size, 0, Math.PI * 2);
            ctx.fill();

            ctx.shadowBlur = 0;
        }
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        updateState();
        drawWave();
        drawWaveParticles();
        drawOrbitingParticles();
        drawOrb();

        requestAnimationFrame(animate);
    }

    animate();

    // Expose state function to Python via window so Eel can find it
    window.setNovaState = function(state) {
        if (['idle', 'talking', 'error'].includes(state)) {
            console.log("NOVA State changed to:", state);
            currentState = state;
        }
    };

    // Register it with Eel explicitly if needed
    if (typeof eel !== 'undefined' && eel.expose) {
        eel.expose(setNovaState);
    }
});
