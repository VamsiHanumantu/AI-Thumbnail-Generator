import { useEffect, useRef, useState } from "react"
import "./App.css"

import {
  createJob,
  subscribeToJob,
  uploadHeadshot,
} from "./api"

function App() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState("")
  const [prompt, setPrompt] = useState("")
  const [numThumbnails, setNumThumbnails] = useState(3)

  const [loading, setLoading] = useState(false)
  const [jobStatus, setJobStatus] = useState("")
  const [error, setError] = useState("")
  const [jobId, setJobId] = useState("")

  const [thumbnails, setThumbnails] = useState([])

  const eventSourceRef = useRef(null)

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  function handleFileChange(e) {
    const selected = e.target.files[0]

    if (!selected) return

    setFile(selected)
    setPreview(URL.createObjectURL(selected))
  }

  async function handleGenerate(e) {
    e.preventDefault()

    if (!file) {
      setError("Please upload a headshot")
      return
    }

    try {
      setLoading(true)
      setError("")
      setThumbnails([])
      setJobStatus("Uploading headshot...")

      // upload image
      const uploadResponse = await uploadHeadshot(file)

      const headshotUrl = uploadResponse.url

      // create job
      setJobStatus("Creating generation job...")

      const jobResponse = await createJob({
        prompt,
        numThumbnails,
        headshotUrl,
      })

      setJobId(jobResponse.job_id)

      setJobStatus("Generating thumbnails...")

      // subscribe SSE
      eventSourceRef.current = subscribeToJob(
        jobResponse.job_id,
        {
          onThumbnailReady: (data) => {
            setThumbnails((prev) => {
              const exists = prev.find(
                (t) => t.id === data.id
              )

              if (exists) return prev

              return [...prev, data]
            })
          },

          onThumbnailFailed: (data) => {
            console.error(data)
          },

          onJobComplete: (data) => {
            setJobStatus(
              `Generation completed`
            )

            setLoading(false)
          },

          onError: (err) => {
            console.error(err)

            setError(
              "Realtime connection failed"
            )

            setLoading(false)
          },
        }
      )
    } catch (err) {
      console.error(err)

      setError(err.message)

      setLoading(false)
    }
  }

  return (
    <div className="app">
      <div className="background-glow glow-1"></div>
      <div className="background-glow glow-2"></div>

      <div className="hero-section">
        <div className="hero-text">
          <span className="badge">
            AI Thumbnail Studio
          </span>

          <h1>
            Generate Viral YouTube
            <span> Thumbnails </span>
            With AI
          </h1>

          <p>
            Create cinematic, high-converting
            thumbnails using Hugging Face,
            FastAPI, SSE streaming, React and
            ImageKit CDN delivery.
          </p>
        </div>

        <div className="generator-card">
          <form onSubmit={handleGenerate}>
            <div className="upload-section">
              <label>
                Upload Headshot
              </label>

              <div className="upload-box">
                {preview ? (
                  <img
                    src={preview}
                    alt="preview"
                    className="preview-image"
                  />
                ) : (
                  <div className="upload-placeholder">
                    <span>+</span>
                    <p>Choose Image</p>
                  </div>
                )}

                <input
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                />
              </div>
            </div>

            <div className="input-group">
              <label>
                Thumbnail Prompt
              </label>

              <textarea
                placeholder="Create a cinematic AI thumbnail about Java backend engineering..."
                value={prompt}
                onChange={(e) =>
                  setPrompt(e.target.value)
                }
                required
              />
            </div>

            <div className="input-group">
              <label>
                Number Of Variations
              </label>

              <select
                value={numThumbnails}
                onChange={(e) =>
                  setNumThumbnails(
                    Number(e.target.value)
                  )
                }
              >
                <option value={1}>
                  1 Thumbnail
                </option>
                <option value={2}>
                  2 Thumbnails
                </option>
                <option value={3}>
                  3 Thumbnails
                </option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="generate-btn"
            >
              {loading
                ? "Generating..."
                : "Generate AI Thumbnails"}
            </button>
          </form>

          {jobId && (
            <div className="status-card">
              <p>
                <strong>Job ID:</strong>{" "}
                {jobId}
              </p>

              <p>
                <strong>Status:</strong>{" "}
                {jobStatus}
              </p>
            </div>
          )}

          {error && (
            <div className="error-box">
              {error}
            </div>
          )}
        </div>
      </div>

      {loading && (
        <div className="loading-container">
          <div className="loader"></div>
          <p>Generating thumbnails...</p>
        </div>
      )}

      {thumbnails.length > 0 && (
        <div className="results-section">
          <div className="section-header">
            <h2>Generated Thumbnails</h2>

            <p>
              Live AI-generated results streamed
              using Server Sent Events
            </p>
          </div>

          <div className="thumbnail-grid">
            {thumbnails.map((thumbnail) => (
              <div
                key={thumbnail.id}
                className="thumbnail-card"
              >
                <div className="card-top">
                  <span className="style-tag">
                    {thumbnail.style_name.replace(
                      "_",
                      " "
                    )}
                  </span>

                  <span className="success-tag">
                    Ready
                  </span>
                </div>

                <img
                  src={
                    thumbnail?.variants
                      ?.youtube ||
                    thumbnail.imagekit_url
                  }
                  alt={thumbnail.style_name}
                />

                <div className="card-footer">
                  <a
                    href={thumbnail.imagekit_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open Full Image
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default App