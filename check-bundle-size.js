const fs = require('fs');
const path= require('path');

const LIMIT_KB = 350;
const DIST_DIR= path.join(__dirname,'dist/scout-pipeline-demo/browser');

const files=fs.readdirSync(DIST_DIR).filter(f => f.endsWith('.js'));

let failed=false;

for (const file of files) {
  const filePath = path.join(DIST_DIR, file);
  const sizeKB= fs.statSync(filePath).size / 1024;
  const status = sizeKB > LIMIT_KB ? 'FAIL' : 'PASS';
  if (status === 'FAIL') failed = true;
  console.log('[${status}] ${file}: ${sizeKB.toFixed(2)} KB (limit: ${LIMIT_KB} KB)');
}

if (failed) {
  console.error('\nBundle size limit exceeded.Reduce bundle size before merging.');
  process.exit(1);

}

console.log('\nAll bundles within size limit.');
