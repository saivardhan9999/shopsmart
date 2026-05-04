const cards = document.querySelectorAll('.reveal');

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.style.animationPlayState = 'running';
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.2 },
);

cards.forEach((card, index) => {
  card.style.animationDelay = `${index * 70}ms`;
  card.style.animationPlayState = 'paused';
  observer.observe(card);
});
