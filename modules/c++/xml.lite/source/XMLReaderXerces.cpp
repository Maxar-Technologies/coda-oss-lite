/* =========================================================================
 * This file is part of xml.lite-c++
 * =========================================================================
 *
 * (C) Copyright 2004 - 2011, General Dynamics - Advanced Information Systems
 *
 * xml.lite-c++ is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this program; If not,
 * see <http://www.gnu.org/licenses/>.
 *
 */

#include "xml/lite/XMLReader.h"

#if defined(USE_XERCES)

sys::Mutex xml::lite::XMLReaderXerces::mMutex;

xml::lite::XercesLocalString::XercesLocalString(const XMLCh *xmlStr)
{
    mLocal = toLocal(xmlStr);
}

xml::lite::XercesLocalString::XercesLocalString(const char *c_str)
{
    mLocal = c_str;
}

xml::lite::XercesLocalString::
XercesLocalString(const XercesLocalString& rhs)
{
    mLocal = rhs.mLocal;
}

XMLCh *xml::lite::XercesLocalString::toXMLCh() const
{
    return XMLString::transcode(mLocal.c_str());
}

xml::lite::XercesLocalString& xml::lite::XercesLocalString::
operator=(const XMLCh *xmlStr)
{
    mLocal = toLocal(xmlStr);
    return *this;
}

xml::lite::XercesLocalString& xml::lite::XercesLocalString::
operator=(const xml::lite::XercesLocalString& rhs)
{
    if (this != &rhs)
    {
        mLocal = rhs.mLocal;
    }
    return *this;
}

std::string xml::lite::XercesLocalString::toLocal(const XMLCh *xmlStr)
{
    char *localCStr = XMLString::transcode(xmlStr);
    std::string local = localCStr;
    XMLString::release(&localCStr);
    return local;
}

void xml::lite::XercesContentHandler::characters(const XMLCh* const chars,
        const XercesSize_T length)
{
    xml::lite::XercesLocalString xstr(chars);
    mLiteHandler->characters(xstr.c_str(), (int)length);
}

void xml::lite::XercesContentHandler::startDocument()
{
    mLiteHandler->startDocument();
}

void xml::lite::XercesContentHandler::endDocument()
{
    mLiteHandler->endDocument();
}

void xml::lite::XercesContentHandler::endElement(const XMLCh *const uri,
        const XMLCh *const localName,
        const XMLCh *const qname)
{
    xml::lite::XercesLocalString xuri(uri);
    xml::lite::XercesLocalString xlocalName(localName);
    xml::lite::XercesLocalString xqname(qname);

    mLiteHandler->endElement(xuri.str(),
                             xlocalName.str(),
                             xqname.str());
}

void xml::lite::XercesContentHandler::
startElement(const XMLCh *const uri,
             const XMLCh *const localName,
             const XMLCh *const qname,
             const XercesAttributesInterface_T &attrs)

{
    // We have to copy the whole array
    LiteAttributes_T attributes;
    for (unsigned int i = 0; i < attrs.getLength(); i++)
    {
        LiteAttributesNode_T attributeNode;
        attributeNode.setQName(
            XercesLocalString(attrs.getQName(i)).str()
        );

        assert(attributeNode.getLocalName() ==
               XercesLocalString(attrs.getLocalName(i)).str()
              );

        attributeNode.setUri(
            XercesLocalString(attrs.getURI(i)).str()
        );

        attributeNode.setValue(
            XercesLocalString(attrs.getValue(i)).str()
        );

        //don't add duplicate attributes
        if (attributes.getIndex(attributeNode.getUri(),
                                  attributeNode.getLocalName()) == -1)
            attributes.add(attributeNode);
    }

    XercesLocalString xuri(uri);
    XercesLocalString xlocalName(localName);
    XercesLocalString xqname(qname);
    mLiteHandler->startElement(xuri.str(),
                               xlocalName.str(),
                               xqname.str(),
                               attributes);
}

void xml::lite::XercesErrorHandler::
warning(const SAXParseException &exception)
{
}

void xml::lite::XercesErrorHandler::
error(const SAXParseException &exception)
{
    XercesLocalString m(exception.getMessage());
    throw(xml::lite::XMLParseException(m.str(),
                                       exception.getLineNumber(),
                                       exception.getColumnNumber()));
}

void xml::lite::XercesErrorHandler::
fatalError(const SAXParseException &exception)
{
    XercesLocalString m(exception.getMessage());
    xml::lite::XMLParseException xex(m.str(),
                                     exception.getLineNumber(),
                                     exception.getColumnNumber());

    throw except::Error(Ctxt(xex.getMessage()));
}

xml::lite::XMLReaderXerces::XMLReaderXerces()
{
    //! XMLPlatformUtils::Initialize is not thread safe!
    try
    {
        mt::CriticalSection<sys::Mutex> cs(&mMutex);
        XMLPlatformUtils::Initialize();
    }
    catch (const ::XMLException& toCatch)
    {
        xml::lite::XercesLocalString local(toCatch.getMessage());
        except::Error e(Ctxt(local.str() + " (Initialization error)"));
        throw(e);
    }
    create();
}

void xml::lite::XMLReaderXerces::parse(io::InputStream & is, int size)
{
    io::ByteStream byteStream;
    is.streamTo(byteStream, size);

    off_t available = byteStream.available();
    if ( available <= 0 )
    {
        throw xml::lite::XMLParseException(Ctxt("No stream available"));
    }
    sys::byte* buffer = new sys::byte[available];
    byteStream.read(buffer, available);

    // Adopt my buffer, and delete it for me
    MemBufInputSource memBuffer((const unsigned char *)buffer,
                                available,
                                XMLReaderXerces::MEM_BUFFER_ID(),
                                false);

    mNative->parse(memBuffer);

    delete [] buffer;
}

void xml::lite::XMLReaderXerces::setValidation(bool validate)
{
    mNative->setFeature(XMLUni::fgSAX2CoreNameSpacePrefixes, true);
    mNative->setFeature(XMLUni::fgXercesSchema, validate);
    mNative->setFeature(XMLUni::fgSAX2CoreValidation, validate); // optional
    mNative->setFeature(XMLUni::fgSAX2CoreNameSpaces, true);     // optional
}

bool xml::lite::XMLReaderXerces::getValidation()
{
    return mNative->getFeature(XMLUni::fgSAX2CoreValidation);
}


// This function creates the parser
void xml::lite::XMLReaderXerces::create()
{
    mDriverContentHandler.reset(new XercesContentHandler());
    mErrorHandler.reset(new XercesErrorHandler());

    mNative.reset(XMLReaderFactory::createXMLReader());
    mNative->setFeature(XMLUni::fgSAX2CoreNameSpacePrefixes, true);
    mNative->setFeature(XMLUni::fgSAX2CoreValidation, false);   // optional
    mNative->setFeature(XMLUni::fgSAX2CoreNameSpaces, true);    // optional
    mNative->setFeature(XMLUni::fgXercesSchema, false);
    mNative->setContentHandler(mDriverContentHandler.get());
    mNative->setErrorHandler(mErrorHandler.get());
}
// This function destroys the parser
void xml::lite::XMLReaderXerces::destroy()
{
    //! this memory must be deleted before the terminate below
    mNative.reset(NULL);
    mDriverContentHandler.reset(NULL);
    mErrorHandler.reset(NULL);

    //! XMLPlatformUtils::Terminate is not thread safe!
    try
    {
        mt::CriticalSection<sys::Mutex> cs(&mMutex);
        XMLPlatformUtils::Terminate();
    }
    catch (const ::XMLException& toCatch)
    {
        xml::lite::XercesLocalString local(toCatch.getMessage());
        except::Error e(Ctxt(local.str() + " (Termination error)"));
        throw (e);
    }
}

#endif
