const { Client } = require('@notionhq/client')
require('dotenv').config()

const express = require('express')
const app = express()
app.use(express.json())
const port = 3000

const notion = new Client({ auth: process.env.NOTION_AUTH });
const databaseId = process.env.NOTION_DATABASE

app.get('/', async (req, res) => {
    let data = await getData()
    res.send(data)
})

app.post('/save', async (req, res) => {
    // console.log(req.body)
    let data = await saveData(req.body.studentName, req.body.attendanceTime)
    res.send(data)
})

async function getData() {
    let returnList = []


    try {
        // get data from notion
        let results = []
        let response = await notion.databases.query({
            database_id: databaseId,
        });
        results.push(...response.results);

        results.forEach((page) => {
            if (page.properties["Student name"].title[0]) {
                returnList.push({
                    studentName: page.properties["Student name"].title[0].plain_text,
                    attendanceTime: page.properties["Attendance Time"].rich_text[0].plain_text
                })
            }
        }
        )
        return returnList
    }
    catch (error) {
        console.error(error);
    }
}

async function saveData(studentName, attendanceTime) {

    try {
        // save data to notion
        let response = await notion.pages.create({
            parent: {
                database_id: databaseId,
            },
            properties: {
                "Student name": {
                    title: [
                        {
                            text: {
                                content: studentName,
                            },
                        },
                    ],
                },
                "Attendance Time": {
                    rich_text: [
                        {
                            text: {
                                content: attendanceTime,
                            },
                        },
                    ],
                },
            },
        });
        return response
    }
    catch (error) {
        console.error(error);
    }
}


app.listen(port, () => {
    console.log(`listening at http://localhost:${port}`)
}
)