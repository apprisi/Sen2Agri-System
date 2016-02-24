#include "otbWrapperApplication.h"
#include "otbWrapperApplicationFactory.h"
#include "otbImage.h"
#include "otbVectorImage.h"
#include "otbMultiChannelExtractROI.h"
#include "otbMultiToMonoChannelExtractROI.h"

#include <vector>

namespace otb
{

namespace Wrapper
{

class PhenoMetricsSplitter : public Application
{
public:    

    typedef PhenoMetricsSplitter Self;
    typedef Application Superclass;
    typedef itk::SmartPointer<Self> Pointer;
    typedef itk::SmartPointer<const Self> ConstPointer;
    itkNewMacro(Self)

    itkTypeMacro(PhenoMetricsSplitter, otb::Application)

    typedef FloatVectorImageType                    InputImageType;
    typedef otb::Image<float, 2>                    InternalImageType;

    /** Filters typedef */
    typedef otb::MultiChannelExtractROI<InputImageType::InternalPixelType,
                                        FloatVectorImageType::InternalPixelType> FilterType1;

    /** Filters typedef */
    typedef otb::MultiToMonoChannelExtractROI<InputImageType::InternalPixelType,
                                              InternalImageType::InternalPixelType> FilterType2;

    typedef otb::ImageFileReader<InputImageType> ReaderType;

private:
    void DoInit()
    {
        SetName("PhenoMetricsSplitter");
        SetDescription("Extracts the phenological parameters in a raster and the flags into another raster.");

        SetDocName("PhenoMetricsSplitter");
        SetDocLongDescription("long description");
        SetDocLimitations("None");
        SetDocAuthors("CIU");
        SetDocSeeAlso(" ");        
        AddDocTag(Tags::Vector);
        AddParameter(ParameterType_String,  "in",   "The phenologic parameters and the flags raster");
        AddParameter(ParameterType_OutputImage, "outparams", "The output phenologic parameters raster.");
        AddParameter(ParameterType_OutputImage, "outflags", "The output flags raster.");
        AddParameter(ParameterType_Int, "compress", "Specifies if output files should be compressed or not.");
        MandatoryOff("compress");
        SetDefaultParameterInt("compress", 0);
    }

    void DoUpdateParameters()
    {
      // Nothing to do.
    }

    void DoExecute()
    {
        std::string inImgStr = GetParameterString("in");
        m_reader = ReaderType::New();
        m_reader->SetFileName(inImgStr);
        m_reader->UpdateOutputInformation();
        int nTotalBands = m_reader->GetOutput()->GetNumberOfComponentsPerPixel();
        if(nTotalBands != 5)
        {
            itkExceptionMacro("Wrong number of bands " << nTotalBands << ". It should be 5!");
        }

        // Set the extract filter input image
        m_FilterParams = FilterType1::New();
        m_FilterParams->SetInput(m_reader->GetOutput());
        // Set the channel to extract
        m_FilterParams->SetFirstChannel(1);
        m_FilterParams->SetLastChannel(4);

        m_FilterFlags = FilterType2::New();
        m_FilterFlags->SetInput(m_reader->GetOutput());
        m_FilterFlags->SetChannel(5);

        m_FilterParams->UpdateOutputInformation();
        m_FilterFlags->UpdateOutputInformation();

        // modify the name if we have compression
        SetParameterString("outparams", GetFileName("outparams"));
        SetParameterString("outflags", GetFileName("outflags"));
        // write the files
        SetParameterOutputImage("outparams", m_FilterParams->GetOutput());
        SetParameterOutputImage("outflags", m_FilterFlags->GetOutput());

        return;
    }

    std::string GetFileName(const std::string &outParamName) {
        bool bUseCompression = (GetParameterInt("compress") != 0);
        std::string ofname = GetParameterString(outParamName);
        std::ostringstream fileNameStream;
        fileNameStream << ofname;
        if(bUseCompression) {
            fileNameStream << "?gdal:co:COMPRESS=DEFLATE";
        }
        return fileNameStream.str();
    }

    ReaderType::Pointer m_reader;
    FilterType1::Pointer        m_FilterParams;
    FilterType2::Pointer        m_FilterFlags;
};

}
}
OTB_APPLICATION_EXPORT(otb::Wrapper::PhenoMetricsSplitter)


