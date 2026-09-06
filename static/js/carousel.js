/* ============================================================
 * carousel.js — 横向叠层滑动卡通用组件（ZBC V1.1）
 * 有界固定高度+分页指示+PC箭头+拖拽+手机swipe+点开聚焦
 * No-Scroll合法补充：同级卡片组横滑，不引发整页纵滚
 * ============================================================ */
(function (global) {
  'use strict';

  function Carousel(container, options) {
    options = options || {};
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    if (!this.container) return;
    this.track = this.container.querySelector('.card-carousel') || this.container;
    this.cards = this.track ? this.track.querySelectorAll('.carousel-card') : [];
    this.currentIndex = 0;
    this.visibleCount = options.visibleCount || this._calcVisibleCount();
    this.totalPages = Math.max(1, Math.ceil(this.cards.length / this.visibleCount));
    this.onCardClick = options.onCardClick || null;
    this._isDragging = false;
    this._dragStartX = 0;
    this._dragScrollLeft = 0;
    this._init();
  }

  Carousel.prototype._calcVisibleCount = function () {
    var w = window.innerWidth;
    if (w <= 640) return 1;
    if (w <= 1024) return 2;
    return 3;
  };

  Carousel.prototype._init = function () {
    var self = this;
    if (!this.track || !this.cards.length) return;

    // 创建导航控件
    this._buildNav();

    // 卡片点击
    this.cards.forEach(function (card, idx) {
      card.addEventListener('click', function (e) {
        if (self._isDragging) { e.preventDefault(); return; }
        if (self.onCardClick) self.onCardClick(card, idx);
      });
    });

    // 滚动监听更新分页
    var scrollTimeout;
    this.track.addEventListener('scroll', function () {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(function () {
        self._updatePagination();
      }, 100);
    });

    // PC拖拽
    this.track.addEventListener('mousedown', function (e) {
      self._isDragging = true;
      self._dragStartX = e.pageX - self.track.offsetLeft;
      self._dragScrollLeft = self.track.scrollLeft;
      self.track.classList.add('is-dragging');
    });
    document.addEventListener('mouseleave', function () {
      self._isDragging = false;
      self.track.classList.remove('is-dragging');
    });
    document.addEventListener('mouseup', function () {
      setTimeout(function () {
        self._isDragging = false;
        self.track.classList.remove('is-dragging');
      }, 50);
    });
    this.track.addEventListener('mousemove', function (e) {
      if (!self._isDragging) return;
      e.preventDefault();
      var x = e.pageX - self.track.offsetLeft;
      var walk = (x - self._dragStartX) * 1.5;
      self.track.scrollLeft = self._dragScrollLeft - walk;
    });

    // 窗口resize重新计算
    window.addEventListener('resize', function () {
      self.visibleCount = self._calcVisibleCount();
      self.totalPages = Math.max(1, Math.ceil(self.cards.length / self.visibleCount));
      self._updatePagination();
      self._updateArrows();
    });

    this._updatePagination();
    this._updateArrows();
  };

  Carousel.prototype._buildNav = function () {
    var self = this;
    // 检查是否已有导航
    var existingNav = this.container.querySelector('.card-carousel__nav');
    if (existingNav) {
      this.nav = existingNav;
      this.dotsContainer = this.nav.querySelector('.card-carousel__dots');
      this.counter = this.nav.querySelector('.card-carousel__counter');
      this.prevBtn = this.nav.querySelector('.card-carousel__arrow--prev');
      this.nextBtn = this.nav.querySelector('.card-carousel__arrow--next');
    } else {
      this.nav = document.createElement('div');
      this.nav.className = 'card-carousel__nav';

      var dotsWrap = document.createElement('div');
      dotsWrap.className = 'card-carousel__dots';
      this.dotsContainer = dotsWrap;

      this.counter = document.createElement('span');
      this.counter.className = 'card-carousel__counter';

      var arrows = document.createElement('div');
      arrows.className = 'card-carousel__arrows';
      this.prevBtn = document.createElement('button');
      this.prevBtn.className = 'card-carousel__arrow card-carousel__arrow--prev';
      this.prevBtn.innerHTML = '‹';
      this.prevBtn.setAttribute('aria-label', '上一页');
      this.nextBtn = document.createElement('button');
      this.nextBtn.className = 'card-carousel__arrow card-carousel__arrow--next';
      this.nextBtn.innerHTML = '›';
      this.nextBtn.setAttribute('aria-label', '下一页');
      arrows.appendChild(this.prevBtn);
      arrows.appendChild(this.nextBtn);

      this.nav.appendChild(dotsWrap);
      this.nav.appendChild(this.counter);
      this.nav.appendChild(arrows);
      this.container.appendChild(this.nav);
    }

    // 构建分页点
    this.dotsContainer.innerHTML = '';
    for (var i = 0; i < this.totalPages; i++) {
      (function (idx) {
        var dot = document.createElement('button');
        dot.className = 'card-carousel__dot' + (idx === 0 ? ' is-active' : '');
        dot.setAttribute('aria-label', '第' + (idx + 1) + '页');
        dot.addEventListener('click', function () {
          self.goToPage(idx);
        });
        self.dotsContainer.appendChild(dot);
      })(i);
    }

    // 箭头事件
    this.prevBtn.addEventListener('click', function () { self.prev(); });
    this.nextBtn.addEventListener('click', function () { self.next(); });
  };

  Carousel.prototype._updatePagination = function () {
    if (!this.track || !this.cards.length) return;
    var cardWidth = this.cards[0].offsetWidth + 12; // gap
    var scrollLeft = this.track.scrollLeft;
    this.currentIndex = Math.round(scrollLeft / cardWidth);
    var page = Math.floor(this.currentIndex / this.visibleCount);
    page = Math.min(page, this.totalPages - 1);

    // 更新点
    var dots = this.dotsContainer.querySelectorAll('.card-carousel__dot');
    dots.forEach(function (d, i) {
      d.classList.toggle('is-active', i === page);
    });

    // 更新计数器
    if (this.counter) {
      this.counter.textContent = (page + 1) + ' / ' + this.totalPages;
    }

    this._updateArrows();
  };

  Carousel.prototype._updateArrows = function () {
    if (!this.track) return;
    var maxScroll = this.track.scrollWidth - this.track.clientWidth;
    if (this.prevBtn) this.prevBtn.disabled = this.track.scrollLeft <= 5;
    if (this.nextBtn) this.nextBtn.disabled = this.track.scrollLeft >= maxScroll - 5;
  };

  Carousel.prototype.goToPage = function (page) {
    if (!this.track || !this.cards.length) return;
    var cardWidth = this.cards[0].offsetWidth + 12;
    var targetScroll = page * this.visibleCount * cardWidth;
    this.track.scrollTo({ left: targetScroll, behavior: 'smooth' });
  };

  Carousel.prototype.prev = function () {
    if (!this.track) return;
    var cardWidth = this.cards[0] ? this.cards[0].offsetWidth + 12 : 200;
    this.track.scrollBy({ left: -cardWidth * this.visibleCount, behavior: 'smooth' });
  };

  Carousel.prototype.next = function () {
    if (!this.track) return;
    var cardWidth = this.cards[0] ? this.cards[0].offsetWidth + 12 : 200;
    this.track.scrollBy({ left: cardWidth * this.visibleCount, behavior: 'smooth' });
  };

  // 自动初始化所有 data-carousel 元素
  function autoInit() {
    var containers = document.querySelectorAll('[data-carousel]');
    containers.forEach(function (c) {
      if (!c._carouselInstance) {
        c._carouselInstance = new Carousel(c);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    autoInit();
  }

  global.ZBCCarousel = Carousel;
  global.ZBCCarousel.autoInit = autoInit;
  console.log('[carousel] 横向叠层滑动卡组件已加载');
})(window);
