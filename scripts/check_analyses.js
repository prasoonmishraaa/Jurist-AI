const mongoose = require('mongoose');

async function check() {
  try {
    await mongoose.connect(process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/jurist_ai');
    const analyses = await mongoose.connection.db.collection('analyses').find({}).sort({createdAt: -1}).limit(10).toArray();
    console.log('Found ' + analyses.length + ' analyses in MongoDB:');
    analyses.forEach((a, i) => {
      console.log('\n=== [' + i + '] Title: ' + a.caseTitle + ' ===');
      console.log('Category:', a.category, '| Court:', a.court, '| CreatedAt:', a.createdAt);
      console.log('Prediction:', JSON.stringify(a.prediction, null, 2));
      console.log('Input Text Snippet:', (a.inputTextSnippet || '').slice(0, 300));
    });
    await mongoose.disconnect();
  } catch(e) {
    console.log('MongoDB error:', e.message);
  }
}
check();
