document.addEventListener("DOMContentLoaded", () => {
    const menuButton = document.getElementById("menu-button");
    const menu = document.getElementById("main-menu");
    if (menuButton && menu) {
        menuButton.addEventListener("click", () => {
            const open = menu.classList.toggle("open");
            menuButton.setAttribute("aria-expanded", String(open));
        });
    }

    const description = document.getElementById("descripcion");
    const charCount = document.getElementById("char-count");
    if (description && charCount) {
        const updateCount = () => {
            charCount.textContent = String(description.value.length);
        };
        description.addEventListener("input", updateCount);
        updateCount();
    }

    const imageInput = document.getElementById("fotografia");
    const preview = document.getElementById("image-preview");
    if (imageInput && preview) {
        imageInput.addEventListener("change", () => {
            preview.replaceChildren();
            const file = imageInput.files[0];
            if (!file || !file.type.startsWith("image/")) {
                preview.hidden = true;
                return;
            }
            const img = document.createElement("img");
            img.alt = "Vista previa de la fotografía";
            img.src = URL.createObjectURL(file);
            img.addEventListener("load", () => URL.revokeObjectURL(img.src));
            preview.appendChild(img);
            preview.hidden = false;
        });
    }

    const form = document.getElementById("reclamo-form");
    if (form) {
        form.addEventListener("submit", (event) => {
            let valid = true;
            form.querySelectorAll("[required]").forEach((field) => {
                if (!field.value.trim()) {
                    valid = false;
                    field.classList.add("invalid");
                } else {
                    field.classList.remove("invalid");
                }
            });
            if (!valid) {
                event.preventDefault();
                const firstInvalid = form.querySelector(".invalid");
                if (firstInvalid) firstInvalid.focus();
            }
        });
    }
});
