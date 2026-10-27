const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/home/shuni/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1000, height: 900 }, deviceScaleFactor: 4 });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await p.goto('file:///home/shuni/projects/portfolio/visitka.html', { waitUntil: 'networkidle', timeout: 40000 });
  await p.waitForTimeout(600);

  // PDF: 96×56 мм (90×50 + 3 мм вылеты), две страницы
  await p.pdf({
    path: 'assets/visitka.pdf',
    width: '96mm', height: '56mm',
    printBackground: true,
    margin: { top: 0, right: 0, bottom: 0, left: 0 },
    pageRanges: '1-2'
  });

  // PNG для мессенджеров
  for (const [i, name] of [[0, 'front'], [1, 'back']]) {
    await p.locator('.card').nth(i).screenshot({ path: `shots/visitka-${name}.png` });
  }

  // проверка содержимого
  console.log(JSON.stringify(await p.evaluate(() => ({
    cards: document.querySelectorAll('.card').length,
    qrs: [...document.querySelectorAll('.qr-box img')].map(i => i.src.split('/').pop() + ' ' + i.naturalWidth + 'px'),
    front: document.querySelector('.name')?.innerText.replace(/\n/g, ' '),
    contacts: [...document.querySelectorAll('.line .v')].map(e => e.textContent),
    steps: document.querySelectorAll('ol.steps li').length,
    bullets: document.querySelectorAll('ul.list li').length
  })), null, 1));
  console.log('ошибки:', errs.length ? JSON.stringify(errs) : 'нет');
  await b.close();
})();
