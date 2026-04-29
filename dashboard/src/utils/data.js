import Papa from 'papaparse';

export const loadResults = async () => {
  return new Promise((resolve, reject) => {
    Papa.parse('/data/simulation_results.csv', {
      download: true,
      header: true,
      dynamicTyping: true,
      complete: (results) => {
        const uniqueData = [];
        const seen = new Set();
        results.data.forEach(row => {
          const key = `${row.Constituency}-${row.District}`;
          if (row.Constituency && !seen.has(key)) {
            uniqueData.push(row);
            seen.add(key);
          }
        });
        resolve(uniqueData);
      },
      error: (error) => {
        reject(error);
      }
    });
  });
};

export const loadMetadata = async () => {
  return new Promise((resolve, reject) => {
    Papa.parse('/data/assembly_metadata_enriched.csv', {
      download: true,
      header: true,
      dynamicTyping: true,
      complete: (results) => {
        resolve(results.data.filter(row => row.Constituency));
      },
      error: (error) => {
        reject(error);
      }
    });
  });
};

export const getSummary = (data) => {
  const summary = {
    SPA: 0,
    'AIADMK+': 0,
    TVK: 0,
    Others: 0,
    Total: 0,
    HighestMargin: { constituency: '', party: '', margin: 0 },
    ClosestContest: { constituency: '', party: '', margin: Infinity }
  };

  data.forEach(row => {
    if (row.Winner) {
      summary[row.Winner]++;
      summary.Total++;
      
      if (row.Margin_Votes > summary.HighestMargin.margin) {
        summary.HighestMargin = { constituency: row.Constituency, party: row.Winner, margin: row.Margin_Votes };
      }
      
      if (row.Margin_Votes < summary.ClosestContest.margin && row.Margin_Votes > 0) {
        summary.ClosestContest = { constituency: row.Constituency, party: row.Winner, margin: row.Margin_Votes };
      }
    }
  });

  return summary;
};
