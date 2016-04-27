/*=========================================================================
  *
  * Program:      Sen2agri-Processors
  * Language:     C++
  * Copyright:    2015-2016, CS Romania, office@c-s.ro
  * See COPYRIGHT file for details.
  *
  * Unless required by applicable law or agreed to in writing, software
  * distributed under the License is distributed on an "AS IS" BASIS,
  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  * See the License for the specific language governing permissions and
  * limitations under the License.

 =========================================================================*/
 
#include <vector>

#include <itkImage.h>
#include <itkRGBPixel.h>

#include <otbWrapperTypes.h>

template<typename T>
itk::RGBPixel<float> Lerp(float t, const itk::RGBPixel<T> &p1, const itk::RGBPixel<T> &p2)
{
    itk::RGBPixel<T> result;
    result[0] = p1[0] * (1.0f - t) + p2[0] * t;
    result[1] = p1[1] * (1.0f - t) + p2[1] * t;
    result[2] = p1[2] * (1.0f - t) + p2[2] * t;
    return result;
}

template<typename T>
itk::RGBPixel<T> Round(const itk::RGBPixel<float> &p)
{
    itk::RGBPixel<T> result;
    result[0] = p[0] + 0.5f;
    result[1] = p[1] + 0.5f;
    result[2] = p[2] + 0.5f;
    return result;
}

struct RampEntry
{
    float min;
    float max;
    itk::RGBPixel<uint8_t> minColor;
    itk::RGBPixel<uint8_t> maxColor;

    RampEntry(float min, float max, itk::RGBPixel<uint8_t> minColor, itk::RGBPixel<uint8_t> maxColor)
        : min(min), max(max), minColor(minColor), maxColor(maxColor)
    {
    }
};

typedef std::vector<RampEntry> Ramp;

class ContinuousColorMappingFunctor
{
public:
    typedef otb::Wrapper::FloatVectorImageType InputImageType;
    typedef InputImageType::PixelType InputPixelType;

    typedef itk::RGBPixel<uint8_t> OutputPixelType;
    typedef itk::Image<OutputPixelType> OutputImageType;

    ContinuousColorMappingFunctor()
    {
    }

    void SetRamp(std::vector<RampEntry> ramp)
    {
        m_Ramp = std::move(ramp);
    }

    void SetBandIndex(int bandIdx)
    {
        m_BandIdx = bandIdx;
    }

    const Ramp & GetNoDataValue() const
    {
        return m_Ramp;
    }

    OutputPixelType operator()(const InputPixelType &in) const
    {
        OutputPixelType result;
        result.Fill(0);

        for (const auto &entry : m_Ramp)
        {
            if (in[m_BandIdx] >= entry.min && in[m_BandIdx] < entry.max)
            {
                float t = (in[m_BandIdx] - entry.min) / (entry.max - entry.min);
                result = Round<uint8_t>(Lerp(t, entry.minColor, entry.maxColor));
                break;
            }
        }

        return result;
    }

private:
    Ramp m_Ramp;
    int m_BandIdx;
};
