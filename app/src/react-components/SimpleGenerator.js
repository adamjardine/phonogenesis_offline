import React from "react";

import QuestionBlock from "./QuestionBlock";
import ToolBar from "./ToolBar";
import {withRouter} from "react-router-dom";
import Button from "@material-ui/core/Button";
import Grid from "@material-ui/core/Grid";
import TextField from "@material-ui/core/TextField";
import {FormGroup, Select} from "@material-ui/core";
import FormControl from "@material-ui/core/FormControl";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Switch from "@material-ui/core/Switch";
import "./SimpleGenerator.css"
import "./mainstyle.css"
import {genSimpleQuestion, getMorphologyQuestion, getRuleFamilies} from "../actions/quiz";
import {adjustFooter, footer, theme} from "../App";
import {ThemeProvider} from '@material-ui/styles';


const QUESTION_SIZE_MIN = 15;
const QUESTION_SIZE_MAX = 30;

class SimpleGenerator extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            footerClass: "copyright-info abs-bottom",
            selectedFamily: "Random",
            sizeSelectWarn: "",
            selectedRuleType: "Random",
            selectedQuestionType: "Simple",
            canChangeFamily: true,
            canChangeType: true,
            qType: "Simple",
            isShuffle: true,
            isIPAg: true,
            rule_families: null,
            question: null,
            isWaitingResponse: false
        };
        getRuleFamilies(this);
        this.questionBlockElement = React.createRef();
    }

    onGetQuestion = () => {
        this.setState({isWaitingResponse: true});

        if (this.state.selectedQuestionType === "Simple") {
            const selectedSize = parseInt(document.getElementById("size-input-field").value);
            if (this.state.sizeSelectWarn !== "" || isNaN(selectedSize)) {
                alert("Invalid size!");
                return;
            }

            genSimpleQuestion(this, this.state.isShuffle, this.state.isIPAg, selectedSize,
                this.state.selectedRuleType, this.state.selectedFamily, this.updateQuestionBlock);
        } else if (this.state.selectedQuestionType === "Morphology") {
            getMorphologyQuestion(this, this.state.isShuffle, this.state.isIPAg, this.state.selectedRuleType,
                this.state.selectedFamily, this.updateQuestionBlock)
        } else {
            this.setState({isWaitingResponse: false});
        }


        this.forceUpdate();
    };

    updateQuestionBlock = () => {
        if (this.questionBlockElement.current) {
            this.questionBlockElement.current.resetState();
        }
    };

    onRuleTypeChange = (e) => {
        const targetVal = e.target.value;
        this.setState({selectedRuleType: targetVal});

        if (targetVal !== "Random") {
            this.setState({canChangeFamily: false, selectedFamily: "Random"});
        } else {
            this.setState({canChangeFamily: true});
        }
    };

    validateSizeSelection = (e) => {
        const selSize = parseInt(e.target.value);

        if (selSize < QUESTION_SIZE_MIN || selSize > QUESTION_SIZE_MAX) {
            this.setState({sizeSelectWarn: "out of range"});
        } else {
            this.setState({sizeSelectWarn: ""});
        }
    };

    onFamilyChange = (e) => {
        const targetVal = e.target.value;
        this.setState({selectedFamily: targetVal});

        if (targetVal !== "Random") {
            this.setState({canChangeType: false, selectedType: "Random"});
        } else {
            this.setState({canChangeType: true});
        }
    };

    onShuffleChange = () => {
        this.setState({isShuffle: !this.state.isShuffle});
    };

    onIPAgChange = () => {
        this.setState({isIPAg: !this.state.isIPAg});
    };

    onQuestionTypeChange = (e) => {
        this.setState({selectedQuestionType: e.target.value});
    };

    componentDidUpdate(prevProps, prevState, snap) {
        if (!this.props.isInnerComp) {
            adjustFooter(this);
        }
    };

    componentDidMount() {
        if (!this.props.isInnerComp) {
            adjustFooter(this);
        }
    }

    render() {
        if (this.state.rule_families === null) {
            return <div/>
        }

        return (
            <ThemeProvider theme={theme}>
                {this.props.isInnerComp ? null : <ToolBar history={this.props.history} app={this.props.app}/>}
                <div className={this.props.isInnerComp ? null : "main-area"}>
                    <Grid container direction="row" justify="center" alignItems="flex-start" spacing={3}
                          id={"gen-form"}>

                        <Grid item><FormControl variant="outlined" id={"rule-select-form"}>
                            <InputLabel id={"qtype-sel-label"}>Question Type</InputLabel>
                            <Select labelId="qtype-sel-label" label={"Question Type"}
                                    disabled={this.state.isWaitingResponse}
                                    onChange={this.onQuestionTypeChange.bind(this)}
                                    value={this.state.selectedQuestionType}
                                    id={"qtype-select"}>
                                <MenuItem value={"Simple"}>Simple</MenuItem>
                                <MenuItem value={"Morphology"}>Morphology</MenuItem>
                            </Select>
                        </FormControl>
                        </Grid>

                        <Grid item><FormControl variant="outlined" id={"rule-select-form"}>
                            <InputLabel id={"family-sel-label"}>Rule Family</InputLabel>
                            <Select labelId="family-sel-label" label={"Rule Family"}
                                    disabled={!this.state.canChangeFamily}
                                    onChange={this.onFamilyChange.bind(this)} value={this.state.selectedFamily}
                                    id={"family-select"}>
                                <MenuItem value={"Random"}>Random</MenuItem>
                                {this.state.rule_families.map(family =>
                                    <MenuItem key={family} value={family}>{family}</MenuItem>
                                )}
                            </Select>
                        </FormControl>
                        </Grid>

                        <Grid item><FormControl variant="outlined" disabled={!this.state.canChangeType}>
                            <InputLabel id="rule-type-sel-label">Rule Type</InputLabel>
                            <Select labelId="rule-type-sel-label" id={"rule-type-sel"} label={"Rule Type"}
                                    value={this.state.selectedRuleType} onChange={this.onRuleTypeChange}>
                                <MenuItem value={"Random"}>Random</MenuItem>
                                <MenuItem value={"Alternating"}>Alternating</MenuItem>
                                <MenuItem value={"Neutralizing"}>Neutralizing</MenuItem>
                                <MenuItem value={"Mixed"}>Mixed -
                                    Alternating & Neutralizing</MenuItem>
                            </Select>
                        </FormControl></Grid>

                        {
                            this.state.selectedQuestionType !== "Morphology" ?
                                <Grid item><TextField id={"size-input-field"}
                                                      label="Size(15-30)"
                                                      error={this.state.sizeSelectWarn !== ""}
                                                      helperText={this.state.sizeSelectWarn}
                                                      type="number"
                                                      variant="outlined"
                                                      InputLabelProps={{
                                                          shrink: true,
                                                      }}
                                                      defaultValue={15}
                                                      onBlur={this.validateSizeSelection}/></Grid> : null
                        }

                        <Grid item><FormGroup id={"gen-switches"}>
                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={this.state.isShuffle}
                                        onChange={this.onShuffleChange}
                                        color="primary"
                                    />
                                }
                                label="Shuffle"
                            />
                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={this.state.isIPAg}
                                        onChange={this.onIPAgChange}
                                        color="primary"
                                    />
                                }
                                label="IPA [ɡ]"
                            />
                        </FormGroup></Grid>

                        <Grid item>
                            <Button variant="contained" color="primary" disabled={this.state.isWaitingResponse}
                                    onClick={this.onGetQuestion}>Generate Data</Button>
                        </Grid>
                    </Grid>

                    {this.state.question ?
                        <QuestionBlock ref={this.questionBlockElement} question={this.state.question} isReadOnly={false}
                                       showAnswer={false} isQuiz={false} simpleGen={true}/> : null}
                </div>

                {this.props.isInnerComp ? null : footer(this)}
            </ThemeProvider>
        );
    };
}

export default withRouter(SimpleGenerator);
