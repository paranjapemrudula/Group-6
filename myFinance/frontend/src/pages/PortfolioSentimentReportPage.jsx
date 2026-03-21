import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from 'chart.js'
import { Bar, Doughnut } from 'react-chartjs-2'
import AppShell from '../components/AppShell'
import { api } from '../lib/api'

ChartJS.register(ArcElement, CategoryScale, LinearScale, BarElement, Tooltip, Legend)

function PortfolioSentimentReportPage() {
  const { id } = useParams()
  const [portfolio, setPortfolio] = useState(null)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const loadReport = async () => {
      setLoading(true)
      try {
        const [portfolioResponse, sentimentResponse] = await Promise.all([
          api.get(`/api/portfolios/${id}/`),
          api.get(`/api/portfolios/${id}/sentiment/`),
        ])
        setPortfolio(portfolioResponse.data)
        setReport(sentimentResponse.data)
        setError('')
      } catch {
        setError('Could not load the portfolio sentiment report.')
      } finally {
        setLoading(false)
      }
    }

    loadReport()
  }, [id])

  const stockBreakdownChartData = useMemo(() => {
    if (!report?.summary) return null
    return {
      labels: ['Positive', 'Neutral', 'Negative'],
      datasets: [
        {
          data: [
            report.summary.positive_stocks || 0,
            report.summary.neutral_stocks || 0,
            report.summary.negative_stocks || 0,
          ],
          backgroundColor: ['#16a34a', '#64748b', '#dc2626'],
          borderColor: ['#dcfce7', '#e2e8f0', '#fee2e2'],
          borderWidth: 2,
        },
      ],
    }
  }, [report])

  const stockScoreChartData = useMemo(() => {
    if (!report?.stocks?.length) return null
    return {
      labels: report.stocks.map((item) => item.symbol),
      datasets: [
        {
          label: 'Sentiment %',
          data: report.stocks.map((item) => item.sentiment_percent),
          backgroundColor: report.stocks.map((item) => {
            if (item.sentiment_label === 'Positive') return '#16a34a'
            if (item.sentiment_label === 'Negative') return '#dc2626'
            return '#64748b'
          }),
          borderRadius: 10,
        },
      ],
    }
  }, [report])

  const generatedAtText = report?.generated_at ? new Date(report.generated_at).toLocaleString() : 'Not available'

  return (
    <AppShell title="Sentiment Report">
      <section className="dashboard-hero">
        <div>
          <h2>{portfolio?.name || 'Portfolio'} Sentiment Report</h2>
          <p>News-driven sentiment summary for the stocks tracked inside this portfolio.</p>
        </div>
        <div className="actions">
          <button className="button" type="button" onClick={() => window.print()}>
            Print / Save PDF
          </button>
          <Link className="button button-secondary" to={`/portfolios/${id}`}>
            Back to Portfolio
          </Link>
        </div>
      </section>

      {loading ? <p>Loading sentiment report...</p> : null}
      {error ? <p className="form-error">{error}</p> : null}

      {!loading && !error && report ? (
        <>
          <section className="sentiment-report-meta">
            <article className="sentiment-summary-card">
              <p className="muted">Report generated</p>
              <h4>{generatedAtText}</h4>
            </article>
            <article className="sentiment-summary-card">
              <p className="muted">Avg. sentiment</p>
              <h4>{report.summary?.label || 'Neutral'}</h4>
              <strong>{report.summary?.avg_sentiment ?? report.summary?.average_sentiment_percent ?? 50}%</strong>
            </article>
            <article className="sentiment-summary-card">
              <p className="muted">Article coverage</p>
              <h4>{report.summary?.total_articles || 0}</h4>
              <strong>{report.summary?.tracked_stocks || 0} tracked stocks</strong>
            </article>
            <article className="sentiment-summary-card">
              <p className="muted">Positive count</p>
              <h4>{report.summary?.positive_count || 0}</h4>
              <strong>{report.summary?.positive_stocks || 0} positive stocks</strong>
            </article>
            <article className="sentiment-summary-card">
              <p className="muted">Neutral count</p>
              <h4>{report.summary?.neutral_count || 0}</h4>
              <strong>{report.summary?.neutral_stocks || 0} neutral stocks</strong>
            </article>
            <article className="sentiment-summary-card">
              <p className="muted">Negative count</p>
              <h4>{report.summary?.negative_count || 0}</h4>
              <strong>{report.summary?.negative_stocks || 0} negative stocks</strong>
            </article>
            <article className="sentiment-summary-card">
              <p className="muted">Price direction</p>
              <h4>
                {report.summary?.price_direction_emoji || '->'} {(report.summary?.price_direction || 'flat').toUpperCase()}
              </h4>
              <strong>Portfolio price tone</strong>
            </article>
          </section>

          <section className="dashboard-grid sentiment-report-grid">
            <article className="feature-card">
              <div className="market-card-head">
                <h3>Stock Breakdown</h3>
              </div>
              {stockBreakdownChartData ? (
                <div className="chart-wrap">
                  <Doughnut
                    data={stockBreakdownChartData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: { legend: { position: 'bottom' } },
                    }}
                  />
                </div>
              ) : (
                <p className="muted">Breakdown data is not available.</p>
              )}
            </article>

            <article className="feature-card">
              <div className="market-card-head">
                <h3>Stock Sentiment Scorecard</h3>
              </div>
              {stockScoreChartData ? (
                <div className="chart-wrap">
                  <Bar
                    data={stockScoreChartData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: { legend: { display: false } },
                      scales: {
                        y: {
                          beginAtZero: true,
                          max: 100,
                          title: { display: true, text: 'Sentiment %' },
                        },
                      },
                    }}
                  />
                </div>
              ) : (
                <p className="muted">No stock sentiment scores were available.</p>
              )}
            </article>
          </section>

          <section className="analysis-panel">
            <div className="analysis-panel-head">
              <h3>Sentiment Summary Table</h3>
            </div>
            {report.stocks?.length ? (
              <div className="sentiment-report-table-wrap">
                <table className="sentiment-report-table">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Avg. Sentiment</th>
                      <th>Positive</th>
                      <th>Neutral</th>
                      <th>Negative</th>
                      <th>Price Direction</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.stocks.map((item) => (
                      <tr key={`summary-${item.stock_id}`}>
                        <td>{item.symbol}</td>
                        <td>{item.avg_sentiment ?? item.sentiment_percent}%</td>
                        <td>{item.positive_count ?? item.positive_articles ?? 0}</td>
                        <td>{item.neutral_count ?? item.neutral_articles ?? 0}</td>
                        <td>{item.negative_count ?? item.negative_articles ?? 0}</td>
                        <td>
                          {item.price_direction_emoji || '->'} {(item.price_direction || 'flat').toUpperCase()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="muted">No sentiment summary rows were available.</p>
            )}
          </section>

          <section className="analysis-panel">
            <div className="analysis-panel-head">
              <h3>Stock-Level Findings</h3>
            </div>
            {report.stocks?.length ? (
              <div className="sentiment-stock-list">
                {report.stocks.map((item) => (
                  <article key={item.stock_id} className="sentiment-stock-card">
                    <div className="sentiment-stock-head">
                      <div>
                        <h4>
                          {item.symbol} <span>{item.company_name}</span>
                        </h4>
                        <p className="muted">{item.sector}</p>
                      </div>
                      <div className={`sentiment-badge sentiment-${item.sentiment_label.toLowerCase()}`}>
                        {item.sentiment_label} {item.sentiment_percent}%
                      </div>
                    </div>
                    <p className="muted">
                      Coverage: {item.coverage_count} article{item.coverage_count === 1 ? '' : 's'} | Positive{' '}
                      {item.positive_count ?? item.positive_articles} | Neutral {item.neutral_count ?? item.neutral_articles} |
                      Negative {item.negative_count ?? item.negative_articles} | Price{' '}
                      {item.price_direction_emoji || '->'} {(item.price_direction || 'flat').toUpperCase()}
                    </p>
                    {item.articles?.length ? (
                      <div className="sentiment-headline-list">
                        {item.articles.map((article) => (
                          <a
                            key={article.link}
                            href={article.link}
                            target="_blank"
                            rel="noreferrer"
                            className="sentiment-headline-item"
                          >
                            <strong>{article.title}</strong>
                            <span>
                              {article.publisher || 'Source'} | {article.sentiment_label} |{' '}
                              {article.published_at
                                ? new Date(article.published_at * 1000).toLocaleDateString()
                                : 'Recent'}
                            </span>
                          </a>
                        ))}
                      </div>
                    ) : (
                      <p className="muted">No recent headlines were available for this stock.</p>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <p className="muted">No stock news was available for this portfolio.</p>
            )}
          </section>

          <section className="analysis-panel">
            <div className="analysis-panel-head">
              <h3>Top Headlines Across The Portfolio</h3>
            </div>
            {report.headlines?.length ? (
              <div className="sentiment-headline-list">
                {report.headlines.map((headline) => (
                  <a
                    key={headline.link}
                    href={headline.link}
                    target="_blank"
                    rel="noreferrer"
                    className="sentiment-headline-item"
                  >
                    <strong>
                      {headline.symbol} | {headline.title}
                    </strong>
                    <span>
                      {headline.publisher || 'Source'} | {headline.sentiment_label} |{' '}
                      {headline.published_at ? new Date(headline.published_at * 1000).toLocaleDateString() : 'Recent'}
                    </span>
                  </a>
                ))}
              </div>
            ) : (
              <p className="muted">No cross-portfolio headlines were available.</p>
            )}
          </section>
        </>
      ) : null}
    </AppShell>
  )
}

export default PortfolioSentimentReportPage
