const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/home/shuni/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox'] });
  const p = await b.newPage();
  await p.goto('file:///home/shuni/projects/portfolio/resume.html', { waitUntil: 'load' });
  await p.waitForTimeout(600);
  await p.pdf({
    path: '/home/shuni/projects/portfolio/assets/CV_Oleg_Sparber.pdf',
    printBackground: true,
    preferCSSPageSize: true
  });
  console.log('pdf готов');
  await b.close();
})();
